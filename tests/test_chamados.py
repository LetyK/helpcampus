from app import db
from app.models import Chamado, Historico


def test_abrir_chamado_registra_historico(entrar, abrir_chamado):
    entrar("ana@escola.br")
    chamado = abrir_chamado()
    assert chamado.status == "aberto"
    assert chamado.solicitante.email == "ana@escola.br"
    assert [h.tipo for h in chamado.historico] == ["abertura"]


def test_abrir_chamado_valida_campos(client, entrar):
    entrar("ana@escola.br")
    resp = client.post("/chamados/novo", data={"titulo": "oi", "descricao": "", "prioridade": "x"})
    texto = resp.get_data(as_text=True)
    assert "pelo menos 5 caracteres" in texto
    assert "Escolha uma categoria" in texto
    assert Chamado.query.count() == 0


def test_solicitante_ve_apenas_os_proprios(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    da_ana = abrir_chamado("Chamado da Ana")
    entrar("bruno@escola.br")
    abrir_chamado("Chamado do Bruno")

    lista = client.get("/chamados").get_data(as_text=True)
    assert "Chamado do Bruno" in lista
    assert "Chamado da Ana" not in lista
    assert client.get(f"/chamados/{da_ana.id}").status_code == 404


def test_atendente_ve_todos(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    abrir_chamado("Chamado da Ana")
    entrar("bruno@escola.br")
    abrir_chamado("Chamado do Bruno")
    entrar("carla@escola.br")
    lista = client.get("/chamados").get_data(as_text=True)
    assert "Chamado da Ana" in lista and "Chamado do Bruno" in lista


def test_atendente_atualiza_e_gera_historico(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    chamado = abrir_chamado()
    entrar("carla@escola.br")
    from app.models import Usuario
    carla = Usuario.query.filter_by(email="carla@escola.br").one()
    client.post(f"/chamados/{chamado.id}/atualizar", data={
        "status": "resolvido", "prioridade": "alta", "responsavel_id": carla.id,
    })
    chamado = db.session.get(Chamado, chamado.id)
    assert chamado.status == "resolvido"
    assert chamado.prioridade == "alta"
    assert chamado.responsavel_id == carla.id
    assert chamado.resolvido_em is not None
    ultima = chamado.historico[-1]
    assert ultima.tipo == "alteracao"
    assert "Resolvido" in ultima.texto and "Carla Atendente" in ultima.texto


def test_solicitante_nao_pode_alterar_status(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    chamado = abrir_chamado()
    resp = client.post(f"/chamados/{chamado.id}/atualizar", data={"status": "resolvido"})
    assert resp.status_code == 403
    assert db.session.get(Chamado, chamado.id).status == "aberto"


def test_resposta_do_solicitante_reabre_chamado(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    chamado = abrir_chamado()
    entrar("carla@escola.br")
    client.post(f"/chamados/{chamado.id}/atualizar", data={"status": "aguardando"})
    entrar("ana@escola.br")
    client.post(f"/chamados/{chamado.id}/comentar", data={"texto": "Segue o print."})
    assert db.session.get(Chamado, chamado.id).status == "em_andamento"
    assert Historico.query.filter_by(tipo="comentario").count() == 1


def test_filtro_e_ordenacao_por_prioridade(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    abrir_chamado("Pedido baixa", "baixa")
    abrir_chamado("Pedido urgente", "urgente")
    abrir_chamado("Pedido media", "media")

    texto = client.get("/chamados?ordem=prioridade").get_data(as_text=True)
    assert texto.index("Pedido urgente") < texto.index("Pedido media") < texto.index("Pedido baixa")

    texto = client.get("/chamados?prioridade=urgente").get_data(as_text=True)
    assert "Pedido urgente" in texto and "Pedido baixa" not in texto


def test_busca_por_numero(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    abrir_chamado("Primeiro pedido")
    segundo = abrir_chamado("Segundo pedido")
    texto = client.get(f"/chamados?q=%23{segundo.id}").get_data(as_text=True)
    assert "Segundo pedido" in texto and "Primeiro pedido" not in texto


def test_arquivados_ficam_fora_da_lista_padrao(client, entrar, abrir_chamado):
    entrar("ana@escola.br")
    chamado = abrir_chamado("Pedido antigo")
    entrar("carla@escola.br")
    client.post(f"/chamados/{chamado.id}/atualizar", data={"status": "arquivado"})
    assert "Pedido antigo" not in client.get("/chamados").get_data(as_text=True)
    assert "Pedido antigo" in client.get("/chamados?status=todos").get_data(as_text=True)
