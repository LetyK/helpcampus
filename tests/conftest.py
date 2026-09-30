import pytest

from app import create_app, db
from app.models import Categoria, Chamado, Usuario


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "teste",
    })
    with app.app_context():
        for nome, email, perfil in [
            ("Ana Aluna", "ana@escola.br", "solicitante"),
            ("Bruno Aluno", "bruno@escola.br", "solicitante"),
            ("Carla Atendente", "carla@escola.br", "atendente"),
            ("Diego Admin", "diego@escola.br", "admin"),
        ]:
            u = Usuario(nome=nome, email=email, perfil=perfil)
            u.definir_senha("senha1234")
            db.session.add(u)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def entrar(client):
    def _entrar(email):
        client.post("/sair")
        return client.post("/entrar", data={"email": email, "senha": "senha1234"})
    return _entrar


@pytest.fixture
def abrir_chamado(client):
    def _abrir(titulo="Nota não lançada", prioridade="media", categoria_id=None):
        if categoria_id is None:
            categoria_id = Categoria.query.first().id
        client.post("/chamados/novo", data={
            "titulo": titulo, "descricao": "A nota da P1 não aparece no portal.",
            "categoria_id": categoria_id, "prioridade": prioridade,
        })
        return Chamado.query.filter_by(titulo=titulo).first()
    return _abrir
