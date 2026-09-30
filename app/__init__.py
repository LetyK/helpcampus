"""HelpCampus - sistema web para gerenciamento de solicitações acadêmicas."""
import os
from datetime import timezone
from zoneinfo import ZoneInfo

from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

FUSO = ZoneInfo("America/Sao_Paulo")


def _database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///helpcampus.db")
    # Alguns provedores ainda entregam o prefixo antigo "postgres://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-troque-esta-chave"),
        SQLALCHEMY_DATABASE_URI=_database_url(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        ITENS_POR_PAGINA=20,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.entrar"
    login_manager.login_message = "Entre com sua conta para continuar."

    from . import models
    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .chamados import bp as chamados_bp
    from .cli import registrar_comandos

    app.register_blueprint(auth_bp)
    app.register_blueprint(chamados_bp)
    app.register_blueprint(admin_bp)
    registrar_comandos(app)

    @app.template_filter("data")
    def formatar_data(valor, formato="%d/%m/%Y %H:%M"):
        if valor is None:
            return "-"
        return valor.replace(tzinfo=timezone.utc).astimezone(FUSO).strftime(formato)

    @app.context_processor
    def rotulos():
        return {
            "STATUS": dict(models.STATUS),
            "PRIORIDADES": dict(models.PRIORIDADES),
            "PERFIS": models.PERFIS,
        }

    @app.errorhandler(403)
    def proibido(_):
        return render_template("erro.html", codigo=403,
                               mensagem="Seu perfil não tem acesso a esta página."), 403

    @app.errorhandler(404)
    def nao_encontrado(_):
        return render_template("erro.html", codigo=404,
                               mensagem="Página ou chamado não encontrado."), 404

    with app.app_context():
        db.create_all()
        models.carga_inicial()

    return app
