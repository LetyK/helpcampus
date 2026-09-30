from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import case, func, or_

from . import db
from .decoradores import equipe_required
from .models import (PESO_PRIORIDADE, PRIORIDADES, STATUS, Categoria, Chamado,
                     Historico, Usuario, agora)

bp = Blueprint("chamados", __name__)

CODIGOS_STATUS = [s for s, _ in STATUS]
CODIGOS_PRIORIDADE = [p for p, _ in PRIORIDADES]
ORDEM_PRIORIDADE = case(PESO_PRIORIDADE, value=Chamado.prioridade)


def _registrar(chamado, tipo, texto):
    db.session.add(Historico(chamado=chamado, autor_id=current_user.id, tipo=tipo, texto=texto))


def _obter(chamado_id):
    chamado = db.session.get(Chamado, chamado_id)
    # 404 também para chamados de outras pessoas: não revela que existem
    if chamado is None or not chamado.pode_ver(current_user):
        abort(404)
    return chamado


@bp.route("/")
@login_required
def inicio():
    return redirect(url_for("chamados.lista"))


@bp.route("/chamados")
@login_required
def lista():
    f = {
        "q": request.args.get("q", "").strip(),
        "status": request.args.get("status", ""),
        "categoria": request.args.get("categoria", type=int),
        "prioridade": request.args.get("prioridade", ""),
        "ordem": request.args.get("ordem", "recentes"),
        "meus": request.args.get("meus", ""),
    }

    consulta = Chamado.query
    if not current_user.e_equipe:
        consulta = consulta.filter(Chamado.solicitante_id == current_user.id)
    elif f["meus"]:
        consulta = consulta.filter(Chamado.responsavel_id == current_user.id)

    # Contagem por situação para as abas (respeita o perfil e o "só os meus")
    contagem = dict(consulta.with_entities(Chamado.status, func.count(Chamado.id))
                    .group_by(Chamado.status).all())
    contagem["ativos"] = sum(n for st, n in contagem.items() if st != "arquivado")

    if f["status"] in CODIGOS_STATUS:
        consulta = consulta.filter(Chamado.status == f["status"])
    elif f["status"] != "todos":
        consulta = consulta.filter(Chamado.status != "arquivado")

    if f["categoria"]:
        consulta = consulta.filter(Chamado.categoria_id == f["categoria"])
    if f["prioridade"] in CODIGOS_PRIORIDADE:
        consulta = consulta.filter(Chamado.prioridade == f["prioridade"])
    if f["q"]:
        termo = f"%{f['q']}%"
        filtro = or_(Chamado.titulo.ilike(termo), Chamado.descricao.ilike(termo))
        if f["q"].lstrip("#").isdigit():
            filtro = or_(filtro, Chamado.id == int(f["q"].lstrip("#")))
        consulta = consulta.filter(filtro)

    if f["ordem"] == "antigos":
        consulta = consulta.order_by(Chamado.criado_em.asc())
    elif f["ordem"] == "prioridade":
        consulta = consulta.order_by(ORDEM_PRIORIDADE.desc(), Chamado.criado_em.asc())
    else:
        consulta = consulta.order_by(Chamado.criado_em.desc())

    pagina = consulta.paginate(per_page=current_app.config["ITENS_POR_PAGINA"],
                               error_out=False)
    categorias = Categoria.query.order_by(Categoria.nome).all()
    return render_template("chamados/lista.html", pagina=pagina, f=f,
                           categorias=categorias, contagem=contagem)


@bp.route("/chamados/novo", methods=["GET", "POST"])
@login_required
def novo():
    categorias = Categoria.query.filter_by(ativa=True).order_by(Categoria.nome).all()
    dados = {"prioridade": "media"}

    if request.method == "POST":
        dados = {
            "titulo": request.form.get("titulo", "").strip(),
            "descricao": request.form.get("descricao", "").strip(),
            "categoria_id": request.form.get("categoria_id", type=int),
            "prioridade": request.form.get("prioridade", "media"),
        }
        erros = []
        if len(dados["titulo"]) < 5:
            erros.append("Escreva um assunto com pelo menos 5 caracteres.")
        if len(dados["titulo"]) > 150:
            erros.append("O assunto pode ter no máximo 150 caracteres.")
        if len(dados["descricao"]) < 10:
            erros.append("Descreva a solicitação com mais detalhes.")
        categoria = db.session.get(Categoria, dados["categoria_id"] or 0)
        if categoria is None or not categoria.ativa:
            erros.append("Escolha uma categoria.")
        if dados["prioridade"] not in CODIGOS_PRIORIDADE:
            erros.append("Escolha uma prioridade.")

        if erros:
            for e in erros:
                flash(e, "erro")
        else:
            chamado = Chamado(
                titulo=dados["titulo"], descricao=dados["descricao"],
                categoria=categoria, prioridade=dados["prioridade"],
                solicitante_id=current_user.id,
            )
            db.session.add(chamado)
            _registrar(chamado, "abertura", "Chamado aberto.")
            db.session.commit()
            flash(f"Chamado #{chamado.id} aberto. Acompanhe as respostas nesta página.", "ok")
            return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))

    return render_template("chamados/novo.html", categorias=categorias, dados=dados)


@bp.route("/chamados/<int:chamado_id>")
@login_required
def detalhe(chamado_id):
    chamado = _obter(chamado_id)
    equipe = []
    if current_user.e_equipe:
        equipe = (Usuario.query.filter(Usuario.perfil.in_(["atendente", "admin"]),
                                       Usuario.ativo.is_(True))
                  .order_by(Usuario.nome).all())
    return render_template("chamados/detalhe.html", c=chamado, equipe=equipe)


@bp.route("/chamados/<int:chamado_id>/comentar", methods=["POST"])
@login_required
def comentar(chamado_id):
    chamado = _obter(chamado_id)
    texto = request.form.get("texto", "").strip()
    if not texto:
        flash("Escreva uma mensagem antes de enviar.", "erro")
    elif chamado.status == "arquivado":
        flash("Chamados arquivados não recebem novas mensagens.", "erro")
    else:
        _registrar(chamado, "comentario", texto)
        # Resposta do solicitante devolve o chamado para a fila da equipe
        if not current_user.e_equipe and chamado.status in ("aguardando", "resolvido"):
            anterior = chamado.status
            chamado.status = "em_andamento" if anterior == "aguardando" else "aberto"
            chamado.resolvido_em = None
            _registrar(chamado, "alteracao",
                       f"Situação: {dict(STATUS)[anterior]} → {dict(STATUS)[chamado.status]}")
        chamado.atualizado_em = agora()
        db.session.commit()
        flash("Mensagem enviada.", "ok")
    return redirect(url_for("chamados.detalhe", chamado_id=chamado.id) + "#historico")


@bp.route("/chamados/<int:chamado_id>/atualizar", methods=["POST"])
@equipe_required
def atualizar(chamado_id):
    chamado = _obter(chamado_id)
    rotulo_status, rotulo_prioridade = dict(STATUS), dict(PRIORIDADES)
    mudancas = []

    status = request.form.get("status")
    if status in CODIGOS_STATUS and status != chamado.status:
        mudancas.append(f"Situação: {rotulo_status[chamado.status]} → {rotulo_status[status]}")
        chamado.status = status
        chamado.resolvido_em = agora() if status == "resolvido" else chamado.resolvido_em
        if status in ("aberto", "em_andamento", "aguardando"):
            chamado.resolvido_em = None

    prioridade = request.form.get("prioridade")
    if prioridade in CODIGOS_PRIORIDADE and prioridade != chamado.prioridade:
        mudancas.append(f"Prioridade: {rotulo_prioridade[chamado.prioridade]} → "
                        f"{rotulo_prioridade[prioridade]}")
        chamado.prioridade = prioridade

    resp_id = request.form.get("responsavel_id", type=int)
    if resp_id != chamado.responsavel_id:
        novo = db.session.get(Usuario, resp_id) if resp_id else None
        if resp_id and (novo is None or not novo.e_equipe):
            flash("Responsável inválido.", "erro")
        else:
            mudancas.append(f"Responsável: {novo.nome if novo else 'ninguém'}")
            chamado.responsavel = novo

    if mudancas:
        _registrar(chamado, "alteracao", "\n".join(mudancas))
        chamado.atualizado_em = agora()
        db.session.commit()
        flash("Chamado atualizado.", "ok")
    return redirect(url_for("chamados.detalhe", chamado_id=chamado.id))
