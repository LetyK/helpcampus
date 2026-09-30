# HelpCampus

Sistema web para registro, acompanhamento e gerenciamento de solicitações acadêmicas (chamados).
Projeto Integrador em Computação II, UNIVESP, 2026, Grupo 9.

## O que o sistema faz

- Cadastro e login com senha criptografada e três perfis: aluno/colaborador, atendente e administrador.
- Abertura de chamados com assunto, categoria, prioridade e descrição.
- Lista com busca, filtros por situação, categoria e prioridade e ordenação por data ou prioridade.
- Histórico completo de cada chamado: mensagens e todas as mudanças de situação, prioridade e responsável.
- Atendentes assumem chamados, mudam a situação e respondem; a resposta do aluno a um chamado "aguardando" devolve o chamado para a fila.
- Painel com totais por situação, prioridade e categoria, chamados sem responsável e tempo médio de resolução.
- Administração de usuários (perfil, ativar/desativar) e de categorias.
- 21 testes automatizados que rodam no GitHub Actions a cada envio.

## Tecnologias

Python 3.12, Flask, SQLAlchemy, Flask-Login, Flask-WTF (proteção CSRF), PostgreSQL em produção e SQLite no desenvolvimento, Gunicorn, pytest, Git/GitHub, Render (nuvem).

## Estrutura

```
app/
  __init__.py      criação da aplicação e configuração
  models.py        tabelas: usuarios, categorias, chamados, historico
  auth.py          entrar, criar conta, sair
  chamados.py      lista, abertura, detalhe, mensagens, atendimento
  admin.py         painel, usuários, categorias
  cli.py           comandos criar-admin e popular-exemplo
  templates/       páginas HTML (Jinja)
  static/          estilo.css e ícone
tests/             testes automatizados (pytest)
render.yaml        configuração de hospedagem no Render
wsgi.py            ponto de entrada do servidor
```

## Rodar no seu computador

Pré-requisito: Python 3.12 instalado.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
flask --app wsgi criar-admin        # pede nome, e-mail e senha
flask --app wsgi popular-exemplo    # opcional: dados de demonstração
flask --app wsgi run --debug
```

Abra http://127.0.0.1:5000. O banco local fica em `instance/helpcampus.db` e é criado sozinho.

Para rodar os testes: `pytest -v`

## Hospedar (GitHub + Neon + Render, tudo gratuito)

A aplicação roda no Render e o banco PostgreSQL fica no Neon. O banco gratuito do próprio Render
é apagado depois de 30 dias, por isso a recomendação é o Neon, que não expira.

### 1. Enviar o código para o GitHub

Crie um repositório vazio em https://github.com/new (sem README) e, na pasta do projeto:

```bash
git init
git add .
git commit -m "HelpCampus: versão inicial"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/helpcampus.git
git push -u origin main
```

Adicione os colegas do grupo em Settings > Collaborators. Na aba Actions dá para ver os testes rodando.

### 2. Criar o banco no Neon

1. Entre em https://neon.tech com a conta do GitHub.
2. Crie um projeto chamado `helpcampus` (região AWS US East, a mesma do Render).
3. Em Connection Details, copie a connection string. Ela começa com `postgresql://` e termina com `?sslmode=require`.

### 3. Publicar no Render

1. Entre em https://render.com com a conta do GitHub.
2. Clique em New > Blueprint e escolha o repositório `helpcampus`. O Render lê o `render.yaml`.
3. Ele vai pedir três valores:
   - `DATABASE_URL`: a connection string do Neon;
   - `ADMIN_EMAIL`: o e-mail do administrador;
   - `ADMIN_PASSWORD`: a senha do administrador.
4. Clique em Apply. O primeiro deploy leva de 2 a 5 minutos.
5. O endereço fica parecido com `https://helpcampus.onrender.com`. Entre com o e-mail e a senha de administrador.

As tabelas, as categorias padrão e o administrador são criados automaticamente na primeira execução.

A cada `git push` na branch `main`, o Render publica a nova versão sozinho.

### Dados de demonstração na nuvem

No seu computador, aponte para o banco do Neon e rode o comando:

```bash
# Linux/macOS
DATABASE_URL="postgresql://...neon.tech/...?sslmode=require" flask --app wsgi popular-exemplo
# Windows (PowerShell)
$env:DATABASE_URL="postgresql://...neon.tech/...?sslmode=require"; flask --app wsgi popular-exemplo
```

Cria um atendente (`atendente@exemplo.com`) e dois alunos, todos com senha `senha1234`.

### Limites do plano gratuito

O serviço gratuito do Render desliga depois de 15 minutos sem acessos e leva cerca de 1 minuto para
voltar no próximo acesso. Antes de apresentar para a tutora, abra o site uns minutos antes.

## Variáveis de ambiente

| Variável         | Uso                                                        |
|------------------|------------------------------------------------------------|
| `SECRET_KEY`     | Assina as sessões de login. O Render gera sozinho.         |
| `DATABASE_URL`   | Endereço do PostgreSQL. Sem ela, usa SQLite local.         |
| `ADMIN_EMAIL`    | Cria o primeiro administrador ao iniciar, se não existir.  |
| `ADMIN_PASSWORD` | Senha desse administrador.                                 |
