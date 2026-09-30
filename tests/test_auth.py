from app.models import Usuario


def test_rotas_protegidas_exigem_login(client):
    for rota in ["/chamados", "/chamados/novo", "/painel", "/admin/usuarios"]:
        resp = client.get(rota)
        assert resp.status_code == 302
        assert "/entrar" in resp.headers["Location"]


def test_cadastro_cria_solicitante_e_entra(client):
    resp = client.post("/cadastro", data={
        "nome": "Eva Estudante", "email": "Eva@Escola.br",
        "senha": "segredo123", "confirmacao": "segredo123",
    }, follow_redirects=True)
    assert "Meus chamados" in resp.get_data(as_text=True)
    usuario = Usuario.query.filter_by(email="eva@escola.br").one()
    assert usuario.perfil == "solicitante"
    assert usuario.senha_hash != "segredo123"


def test_cadastro_recusa_email_repetido_e_senha_curta(client):
    resp = client.post("/cadastro", data={
        "nome": "Outra Ana", "email": "ana@escola.br", "senha": "123", "confirmacao": "123",
    })
    texto = resp.get_data(as_text=True)
    assert "Já existe uma conta" in texto
    assert "pelo menos 8 caracteres" in texto


def test_login_com_senha_errada(client):
    resp = client.post("/entrar", data={"email": "ana@escola.br", "senha": "errada"})
    assert "E-mail ou senha incorretos" in resp.get_data(as_text=True)


def test_conta_desativada_nao_entra(app, client):
    u = Usuario.query.filter_by(email="ana@escola.br").one()
    u.ativo = False
    from app import db
    db.session.commit()
    resp = client.post("/entrar", data={"email": "ana@escola.br", "senha": "senha1234"})
    assert "desativada" in resp.get_data(as_text=True)


def test_login_nao_redireciona_para_outro_site(client):
    resp = client.post("/entrar?next=https://site-malicioso.com",
                       data={"email": "ana@escola.br", "senha": "senha1234"})
    assert resp.headers["Location"].endswith("/chamados")
