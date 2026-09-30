import click

from . import db
from .models import Usuario


def registrar_comandos(app):
    @app.cli.command("criar-admin")
    @click.option("--nome", prompt="Nome")
    @click.option("--email", prompt="E-mail")
    @click.password_option("--senha", prompt="Senha")
    def criar_admin(nome, email, senha):
        """Cria (ou promove) um usuário administrador."""
        email = email.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            usuario = Usuario(nome=nome, email=email)
            db.session.add(usuario)
        usuario.perfil = "admin"
        usuario.definir_senha(senha)
        db.session.commit()
        click.echo(f"Administrador pronto: {email}")


    @app.cli.command("popular-exemplo")
    def popular_exemplo():
        """Cria usuários e chamados fictícios para demonstração (senha: senha1234)."""
        from datetime import timedelta

        from .models import Categoria, Chamado, Historico, agora

        if Chamado.query.first():
            click.echo("Já existem chamados; nada foi criado.")
            return

        def usuario(nome, email, perfil):
            u = Usuario.query.filter_by(email=email).first()
            if u is None:
                u = Usuario(nome=nome, email=email, perfil=perfil)
                u.definir_senha("senha1234")
                db.session.add(u)
            return u

        atendente = usuario("Luan Pereira", "atendente@exemplo.com", "atendente")
        marina = usuario("Marina Costa", "marina@exemplo.com", "solicitante")
        rafael = usuario("Rafael Souza", "rafael@exemplo.com", "solicitante")
        cats = {c.nome: c for c in Categoria.query}

        exemplos = [
            ("Nota da P1 de Cálculo não aparece no portal", "Notas e frequência", "alta",
             "em_andamento", marina, atendente, 3),
            ("Declaração de matrícula para estágio", "Documentos e declarações", "urgente",
             "aberto", rafael, None, 1),
            ("Projetor da sala 12 não liga", "Infraestrutura e manutenção", "media",
             "aguardando", marina, atendente, 5),
            ("Senha do Wi-Fi da biblioteca", "Suporte de TI", "baixa",
             "resolvido", rafael, atendente, 9),
            ("Boleto de setembro com valor diferente", "Financeiro", "alta",
             "aberto", marina, None, 2),
        ]
        for titulo, cat, prio, status, sol, resp, dias in exemplos:
            criado = agora() - timedelta(days=dias, hours=3)
            c = Chamado(titulo=titulo, categoria=cats.get(cat) or Categoria.query.first(),
                        prioridade=prio, status=status, solicitante=sol, responsavel=resp,
                        criado_em=criado,
                        descricao="Chamado de demonstração criado automaticamente.")
            if status == "resolvido":
                c.resolvido_em = criado + timedelta(hours=20)
            db.session.add(c)
            db.session.add(Historico(chamado=c, autor=sol, tipo="abertura",
                                     texto="Chamado aberto.", criado_em=criado))
            if resp:
                db.session.add(Historico(chamado=c, autor=resp, tipo="comentario",
                                         texto="Recebido. Estamos verificando.",
                                         criado_em=criado + timedelta(hours=2)))
        db.session.commit()
        click.echo("Dados de exemplo criados. Senha de todos: senha1234")
