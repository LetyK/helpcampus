from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from . import db
from .decoradores import admin_required, equipe_required
from .models import PERFIS, PRIORIDADES, STATUS, Categoria, Chamado, Usuario

bp = Blueprint("admin", __name__)


@bp.route("/painel")
@equipe_required
def painel():
    por_status = dict(db.session.query(Chamado.status, func.count()).group_by(Chamado.status))
    abertos = Chamado.status.in_(["aberto", "em_andamento", "aguardando"])
    por_prioridade = dict(db.session.query(Chamado.prioridade, func.count())
                          .filter(abertos).group_by(Chamado.prioridade))
    por_categoria = (db.session.query(Categoria.nome, func.count(Chamado.id))
                     .join(Chamado).group_by(Categoria.nome)
                     .order_by(func.count(Chamado.id).desc()).all())
    sem_responsavel = Chamado.query.filter(abertos, Chamado.responsavel_id.is_(None)).count()

    resolvidos = Chamado.query.filter(Chamado.resolvido_em.isnot(None)).all()
    media_horas = None
    if resolvidos:
        total = sum((c.resolvido_em - c.criado_em).total_seconds() for c in resolvidos)
        media_horas = total / len(resolvidos) / 3600

    return render_template(
        "admin/painel.html",
        por_status=[(s, r, por_status.get(s, 0)) for s, r in STATUS],
        por_prioridade=[(p, r, por_prioridade.get(p, 0)) for p, r in reversed(PRIORIDADES)],
        por_categoria=por_categoria,
        sem_responsavel=sem_responsavel,
        media_horas=media_horas,
        total=sum(por_status.values()),
    )


@bp.route("/admin/usuarios", methods=["GET", "POST"])
@admin_required
def usuarios():
    if request.method == "POST":
        usuario = db.session.get(Usuario, request.form.get("id", type=int) or 0)
        if usuario is None:
            flash("Usuário não encontrado.", "erro")
        elif usuario.id == current_user.id:
            flash("Você não pode alterar o próprio perfil.", "erro")
        else:
            perfil = request.form.get("perfil")
            if perfil in PERFIS:
                usuario.perfil = perfil
            usuario.ativo = request.form.get("ativo") == "1"
            db.session.commit()
            flash(f"{usuario.nome} atualizado.", "ok")
        return redirect(url_for("admin.usuarios"))

    lista = Usuario.query.order_by(Usuario.nome).all()
    return render_template("admin/usuarios.html", usuarios=lista)


@bp.route("/admin/categorias", methods=["GET", "POST"])
@admin_required
def categorias():
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "criar":
            nome = request.form.get("nome", "").strip()
            if len(nome) < 3:
                flash("O nome precisa ter pelo menos 3 caracteres.", "erro")
            elif Categoria.query.filter(func.lower(Categoria.nome) == nome.lower()).first():
                flash("Essa categoria já existe.", "erro")
            else:
                db.session.add(Categoria(nome=nome))
                db.session.commit()
                flash(f"Categoria “{nome}” criada.", "ok")
        elif acao == "alternar":
            cat = db.session.get(Categoria, request.form.get("id", type=int) or 0)
            if cat:
                cat.ativa = not cat.ativa
                db.session.commit()
                flash(f"“{cat.nome}” {'ativada' if cat.ativa else 'desativada'}.", "ok")
        return redirect(url_for("admin.categorias"))

    contagem = dict(db.session.query(Chamado.categoria_id, func.count())
                    .group_by(Chamado.categoria_id))
    lista = Categoria.query.order_by(Categoria.nome).all()
    return render_template("admin/categorias.html", categorias=lista, contagem=contagem)
