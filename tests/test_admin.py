from app import db
from app.models import Categoria, Usuario


def test_perfis_de_acesso(client, entrar):
    entrar("ana@escola.br")
    assert client.get("/painel").status_code == 403
    assert client.get("/admin/usuarios").status_code == 403
    entrar("carla@escola.br")
    assert client.get("/painel").status_code == 200
    assert client.get("/admin/usuarios").status_code == 403
    entrar("diego@escola.br")
    assert client.get("/admin/usuarios").status_code == 200
    assert client.get("/admin/categorias").status_code == 200


def test_admin_promove_usuario(client, entrar):
    entrar("diego@escola.br")
    ana = Usuario.query.filter_by(email="ana@escola.br").one()
    client.post("/admin/usuarios", data={"id": ana.id, "perfil": "atendente", "ativo": "1"})
    assert db.session.get(Usuario, ana.id).perfil == "atendente"


def test_admin_nao_altera_o_proprio_perfil(client, entrar):
    entrar("diego@escola.br")
    diego = Usuario.query.filter_by(email="diego@escola.br").one()
    client.post("/admin/usuarios", data={"id": diego.id, "perfil": "solicitante"})
    assert db.session.get(Usuario, diego.id).perfil == "admin"


def test_categoria_desativada_some_da_abertura(client, entrar):
    entrar("diego@escola.br")
    client.post("/admin/categorias", data={"acao": "criar", "nome": "Biblioteca"})
    cat = Categoria.query.filter_by(nome="Biblioteca").one()
    assert ">Biblioteca</option>" in client.get("/chamados/novo").get_data(as_text=True)
    client.post("/admin/categorias", data={"acao": "alternar", "id": cat.id})
    assert ">Biblioteca</option>" not in client.get("/chamados/novo").get_data(as_text=True)


def test_painel_conta_chamados(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    abrir_chamado("Primeiro pedido")
    abrir_chamado("Segundo pedido", "urgente")
    entrar("carla@escola.br")
    texto = client.get("/painel").get_data(as_text=True)
    assert "<strong>2</strong> chamados registrados" in texto
    assert "<strong>2</strong> em aberto sem responsável" in texto
