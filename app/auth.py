from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if current_user.is_authenticated:
        return redirect(url_for("chamados.lista"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.conferir_senha(senha):
            flash("E-mail ou senha incorretos.", "erro")
        elif not usuario.ativo:
            flash("Esta conta foi desativada. Procure a secretaria.", "erro")
        else:
            login_user(usuario, remember=bool(request.form.get("lembrar")))
            destino = request.args.get("next", "")
            # Evita redirecionamento para outro site
            if not destino or urlsplit(destino).netloc:
                destino = url_for("chamados.lista")
            return redirect(destino)

    return render_template("auth/entrar.html")


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("chamados.lista"))

    dados = {}
    if request.method == "POST":
        dados = {
            "nome": request.form.get("nome", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
        }
        senha = request.form.get("senha", "")
        confirmacao = request.form.get("confirmacao", "")

        erros = []
        if len(dados["nome"]) < 3:
            erros.append("Informe seu nome completo.")
        if "@" not in dados["email"]:
            erros.append("Informe um e-mail válido.")
        elif Usuario.query.filter_by(email=dados["email"]).first():
            erros.append("Já existe uma conta com este e-mail.")
        if len(senha) < 8:
            erros.append("A senha precisa ter pelo menos 8 caracteres.")
        if senha != confirmacao:
            erros.append("A confirmação não confere com a senha.")

        if erros:
            for e in erros:
                flash(e, "erro")
        else:
            usuario = Usuario(nome=dados["nome"], email=dados["email"])
            usuario.definir_senha(senha)
            db.session.add(usuario)
            db.session.commit()
            login_user(usuario)
            flash("Conta criada.", "ok")
            return redirect(url_for("chamados.lista"))

    return render_template("auth/cadastro.html", dados=dados)


@bp.route("/sair", methods=["POST"])
@login_required
def sair():
    logout_user()
    return redirect(url_for("auth.entrar"))
