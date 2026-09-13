# NUTRAMOVE

Fundação, autenticação, gestão de profissionais e módulo Student implementados.
Onboarding e isolamento entre profissionais incluídos. Dietas com versionamento e publicação implementadas. Treinos com versionamento e publicação implementados. Evolução física com avaliações, medidas e gráficos implementada. NutraMove AI gera sugestões de dieta/treino pendentes de revisão profissional.

- Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui e Lucide.
- Backend: Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic e Alembic.
- Banco: PostgreSQL 17.
- Infraestrutura local: Docker e Docker Compose.
- Branches: develop para desenvolvimento; main para produção.

## Organização

- frontend/: interface e cliente HTTP.
- backend/: API, autenticação, modelos, migrations e testes.
- infra/: Compose e configuração dos contêineres.
- docs/: [arquitetura](docs/architecture.md), [autenticação](docs/authentication.md)
  e [validações](docs/validation.md).

## Preparar o ambiente

Pré-requisitos: Node.js 24, npm, Python 3.13 e Docker com Compose.
Os comandos a seguir usam PowerShell, partindo da raiz do repositório.

Se ainda não existirem, copie os exemplos:

```powershell
if (!(Test-Path infra/.env)) { Copy-Item infra/.env.example infra/.env }
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (!(Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
```

Defina POSTGRES_PASSWORD em infra/.env e use a mesma senha em DATABASE_URL de
backend/.env. Prefira senha aleatória com caracteres seguros para URL.
Não use placeholders. Os arquivos locais estão ignorados pelo Git.
Nunca inclua secrets em variáveis NEXT_PUBLIC_*: elas são públicas.

O hostname do banco é db no Compose e localhost para Python executado localmente.
Use http://localhost:3000 no navegador, conforme CORS_ORIGINS; 127.0.0.1 é outra origem.

## Backend e PostgreSQL

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d --wait
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic upgrade head
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic check
```

- API: http://localhost:8000
- Health: http://localhost:8000/health
- OpenAPI: http://localhost:8000/docs

Aplique migrations antes de usar o login. Health verifica a API, não o banco.
O contêiner executa como appuser e as portas são publicadas apenas em localhost.

## Criar o primeiro MASTER

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m app.cli.create_master
```

Informe nome, e-mail e senha com confirmação. A senha deve ter 12 a 128 caracteres
e não é exibida no terminal. Não existe usuário ou senha padrão.
A conta é criada apenas por esse comando administrativo, sem cadastro público.

## Frontend

Em outro terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Acesse http://localhost:3000/login. Após entrar, /account exibe sua conta e permite
sair. Sessões usam cookie HttpOnly, sem tokens no localStorage.
A fonte Inter é servida localmente com licença incluída.

No Linux/macOS, use npm em vez de npm.cmd.
No Windows, npm.cmd evita alterar a política de execução do PowerShell.

## Backend local

Dentro de backend/:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --reload --no-access-log
```

Não execute o backend local e o contêiner na mesma porta simultaneamente.
Para manter somente o banco no Docker, execute na raiz:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml stop backend
docker compose --env-file infra/.env -f infra/compose.yaml up -d db --wait
```

No Linux/macOS, o Python do ambiente virtual fica em .venv/bin/python.

## Verificações

Backend, dentro de backend/:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pip check
```

A suíte completa exige PostgreSQL e backend/.env configurados. Os testes de
autenticação usam migrations reais em schema temporário, removido ao final; não
alteram tabelas existentes. Os testes da fundação continuam sem dependência de banco.
A opção no:cacheprovider contorna uma permissão local do cache, sem pular testes.

Frontend, dentro de frontend/:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Compose, na raiz:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
```

Use --quiet para não exibir variáveis resolvidas que possam conter secrets.

## Configuração e limites

SESSION_SECONDS controla a duração absoluta da sessão (padrão: 3600).
COOKIE_SECURE deve ser true em produção, com CORS_ORIGINS usando HTTPS.
O Compose desta etapa é exclusivamente para desenvolvimento local.
Frontend e API devem ser implantados no mesmo site para a política SameSite=Lax.
Requisições POST de autenticação exigem Origin confiável.

Antes de expor publicamente, configure limitação de tentativas de login e a
infraestrutura de produção. Recuperação de senha e MFA não estão implementados.
Veja [autenticação](docs/authentication.md) para decisões e débitos técnicos.

Para parar os serviços preservando o volume de dados:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml down
```


## Gestão de profissionais

MASTER acessa /master após login. Veja [documentação do módulo](docs/professionals.md).
Aplique a migration 20260910_02 com Alembic antes de usar as novas rotas.


## Student e onboarding

Acesse /register para cadastro em seis etapas. O link de cadastro com profissional
fica no detalhe desse profissional na área MASTER. Cadastro sem código fica sem
vínculo e é administrado apenas por MASTER. Login direciona PROFESSIONAL para
/professional e STUDENT para /student.

A migration atual é 20260911_07. Veja [Student](docs/students.md),
[inventário de arquivos](docs/student-files.md) e [contexto atualizado](docs/relatorio-contexto-proximos-prompts.md).
Cadastro público e login ainda precisam de proteção contra abuso antes de exposição pública.


## Dashboards por perfil

Após login e consulta a /auth/me: MASTER abre /master, PROFESSIONAL abre
/professional e STUDENT abre /student. O perfil completo do aluno fica em
/student/profile. Veja [dashboards e navegação](docs/dashboards.md) para métricas,
endpoints, arquivos e validação responsiva. Não houve nova migration nesta etapa.

## Contas locais de demonstracao

Para criar logins MASTER e PROFESSIONAL somente em ENVIRONMENT=development,
execute dentro de backend/:

```powershell
.venv/Scripts/python.exe -m app.cli.create_demo_users
```

O comando cria master.demo@example.com e professional.demo@example.com usando
os servicos existentes. Gera senhas aleatorias e as mostra uma unica vez no terminal.
Guarde-as fora do Git. Repetir o comando preserva contas e senhas existentes.
Nao cria alunos nem dados ficticios de acompanhamento e nao funciona em production/test.
As contas sao locais ao banco configurado; nao sao contas padrao de producao.

## Dietas e versões — Dia 6

Professional acessa Meus alunos → detalhe → Dieta e versões. Student acessa Minha dieta.
MASTER possui leitura. Consulte [dietas](docs/diets.md) para modelos, endpoints, fluxo e validação.
Aplique alembic upgrade head antes de utilizar o módulo.

## Treinos e versões — Dia 7

Professional: Meus alunos → detalhe → Treino e versões. Student: Meu treino.
MASTER consulta sem editar. Aplique alembic upgrade head para instalar a revisão 20260910_05.
Veja [treinos](docs/workouts.md) para modelos, endpoints, permissões, editor e validação.

## Evolução física — Dia 8

Professional acessa Meus alunos → aluno → Evolução para registrar e corrigir avaliações.
Student acessa Minha evolução; MASTER consulta sem editar. Aplique alembic upgrade head
para a revisão 20260911_06. Execute npm.cmd ci no frontend para instalar o Recharts incluído
no lockfile. Veja [evolução](docs/evolution.md) para peso atual, IMC, endpoints e validações.


## Hidratação e reavaliações — Dia 9

Student acessa Hidratação para registrar água e Solicitar reavaliação para
pedir uma revisão do acompanhamento. Professional consulta a hidratação no detalhe
do aluno e atende pedidos em Reavaliações. MASTER possui consulta administrativa.

Aplique `alembic upgrade head` para a revisão `20260911_07` antes de usar as rotas.
`BUSINESS_TIMEZONE` controla o dia de hidratação (padrão America/Sao_Paulo).
A meta permanece em litros/dia, definida pelo profissional; consumo é registrado em ml.
Não há nova dependência nesta etapa. Consulte [hidratação](docs/hydration.md),
[reavaliações](docs/reevaluations.md) e [relatório do Dia 9](docs/dia9-relatorio.md).

## Informativos e notificações internas — Dia 10

Professional publica informativos para toda a carteira ou um aluno próprio. Student lê apenas publicações destinadas a ele; MASTER consulta. O sino no AppShell abre a inbox privada de notificações do User. Aplique `alembic upgrade head` para a revisão `20260912_08`. Consulte [informativos](docs/informations.md) e [notificações](docs/notifications.md).

## Transferência de alunos e auditoria — Dia 11

MASTER transfere ou atribui Student pelo detalhe do aluno. O vínculo muda sem reatribuir histórico; AuditLog registra ator, origem, destino e motivo na mesma transação. Aplique `alembic upgrade head` para a revisão `20260913_09`. Veja [transferências](docs/student-transfers.md) e [auditoria](docs/audit-log.md).

## NutraMove AI — Dia 12

Professional pode gerar sugestões de dieta e treino para alunos ativos da própria carteira. A versão nasce AI_GENERATED/PENDING_REVIEW, é editada e aprovada no fluxo normal. Configure AI_ENABLED e AI_API_KEY no backend/Compose para habilitar. Consulte [NutraMove AI](docs/nutramove-ai.md).
