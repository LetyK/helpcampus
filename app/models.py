import os
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager

PERFIS = {
    "solicitante": "Aluno / colaborador",
    "atendente": "Atendente",
    "admin": "Administrador",
}

PRIORIDADES = [
    ("baixa", "Baixa"),
    ("media", "Média"),
    ("alta", "Alta"),
    ("urgente", "Urgente"),
]
PESO_PRIORIDADE = {"baixa": 1, "media": 2, "alta": 3, "urgente": 4}

STATUS = [
    ("aberto", "Aberto"),
    ("em_andamento", "Em andamento"),
    ("aguardando", "Aguardando solicitante"),
    ("resolvido", "Resolvido"),
    ("arquivado", "Arquivado"),
]

CATEGORIAS_PADRAO = [
    "Secretaria acadêmica",
    "Matrícula e rematrícula",
    "Notas e frequência",
    "Documentos e declarações",
    "Financeiro",
    "Suporte de TI",
    "Infraestrutura e manutenção",
    "Outros",
]


def agora():
    """Horário atual em UTC (sem fuso) para gravar no banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="solicitante")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_active(self):
        return self.ativo

    @property
    def e_equipe(self):
        return self.perfil in ("atendente", "admin")

    @property
    def e_admin(self):
        return self.perfil == "admin"


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    ativa = db.Column(db.Boolean, nullable=False, default=True)


class Chamado(db.Model):
    __tablename__ = "chamados"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    prioridade = db.Column(db.String(10), nullable=False, default="media")
    status = db.Column(db.String(20), nullable=False, default="aberto", index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora, index=True)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=agora, onupdate=agora)
    resolvido_em = db.Column(db.DateTime)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    categoria = db.relationship("Categoria")
    solicitante = db.relationship("Usuario", foreign_keys=[solicitante_id])
    responsavel = db.relationship("Usuario", foreign_keys=[responsavel_id])
    historico = db.relationship(
        "Historico", back_populates="chamado", cascade="all, delete-orphan",
        order_by="Historico.criado_em",
    )

    def pode_ver(self, usuario):
        return usuario.e_equipe or self.solicitante_id == usuario.id


class Historico(db.Model):
    """Linha do tempo do chamado: comentários e mudanças de estado."""
    __tablename__ = "historico"

    id = db.Column(db.Integer, primary_key=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey("chamados.id"), nullable=False, index=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # abertura, comentario, alteracao
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)

    chamado = db.relationship("Chamado", back_populates="historico")
    autor = db.relationship("Usuario")


@login_manager.user_loader
def carregar_usuario(usuario_id):
    return db.session.get(Usuario, int(usuario_id))


def carga_inicial():
    """Cria categorias padrão e o administrador definido nas variáveis de ambiente."""
    if not db.session.query(Categoria.id).first():
        db.session.add_all(Categoria(nome=n) for n in CATEGORIAS_PADRAO)

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    senha = os.environ.get("ADMIN_PASSWORD", "")
    if email and senha and not Usuario.query.filter_by(email=email).first():
        admin = Usuario(nome="Administrador", email=email, perfil="admin")
        admin.definir_senha(senha)
        db.session.add(admin)

    db.session.commit()
