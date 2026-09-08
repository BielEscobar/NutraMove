# NUTRAMOVE

Fundação do projeto, sem funcionalidades de negócio ou autenticação.

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, shadcn/ui e Lucide.
- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic e Alembic.
- **Banco:** PostgreSQL 17.
- **Infraestrutura local:** Docker e Docker Compose.
- **Branches:** `develop` para desenvolvimento e `main` para produção.

## Estrutura

```text
frontend/                Aplicação Next.js independente
backend/
  app/
    main.py              Fábrica da aplicação FastAPI
    api/                 Endpoints HTTP
    core/                Configuração e tratamento de erros
    db/                  Base e sessões SQLAlchemy
    models/              Futuros modelos do banco
    schemas/             Contratos Pydantic
    services/            Futuras regras de negócio
    repositories/        Futuras consultas ao banco
    utils/               Utilitários compartilhados
  tests/                 Testes da fundação
  alembic/               Ambiente e futuras migrations
infra/                   Compose e configuração dos contêineres
docs/                    Documentação e decisões
```

Detalhes em [docs/architecture.md](docs/architecture.md).

## Pré-requisitos

Node.js 24, npm, Python 3.13 e Docker com Compose. Os comandos abaixo são para
PowerShell, a partir da raiz do repositório. Use `npm.cmd` e `npx.cmd` se a política
do PowerShell bloquear os scripts `.ps1`; não é necessário alterar essa política.
No Linux/macOS, use `npm`, `npx` e `.venv/bin/python`.

## 1. Configurar o ambiente local

Copie os exemplos somente se os arquivos de destino ainda não existirem:

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

Defina uma senha local em `infra/.env` (`POSTGRES_PASSWORD`) e use a mesma senha
na `DATABASE_URL` de `backend/.env`. Prefira uma senha aleatória com caracteres
seguros para URL, como hexadecimal. Não use os placeholders dos exemplos.
No Compose, o hostname do banco é `db`; no backend executado localmente, é
`localhost`. O Compose monta a URL automaticamente a partir de `infra/.env`.

Os arquivos `.env` estão ignorados pelo Git. Nunca adicione secrets aos exemplos.
O prefixo `NEXT_PUBLIC_` torna uma variável pública no frontend.

## 2. Iniciar backend e PostgreSQL

Com o Docker em execução:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d --wait
```

- API: http://localhost:8000
- Health: http://localhost:8000/health → `{"status":"ok"}`
- Documentação OpenAPI: http://localhost:8000/docs

O Compose inicia apenas backend e banco. O frontend roda localmente nesta etapa.
O endpoint de health verifica a API, não a disponibilidade do banco.

Para consultar logs e parar os contêineres preservando os dados:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml logs backend
docker compose --env-file infra/.env -f infra/compose.yaml down
```

## 3. Iniciar o frontend

Em outro terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Acesse http://localhost:3000. A página inicial contém apenas a identificação do
NUTRAMOVE. Não há integração de negócio com a API.

## Backend local e ferramentas de desenvolvimento

Para executar testes ou desenvolver fora do contêiner:

```powershell
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m uvicorn app.main:create_app --factory --reload
```

Não execute o backend local simultaneamente ao contêiner na mesma porta.
Se desejar apenas PostgreSQL no Docker, pare o backend do Compose e use:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d db
```

Esse último comando deve ser executado na raiz do repositório.

## Verificações

Backend, dentro de `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pip check
```

Os testes não dependem de PostgreSQL nem de um `.env` local.

Frontend, dentro de `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Não foi adicionado um framework de testes ao frontend estático nesta etapa.
O lint, o typecheck e o build validam sua fundação.

Compose, na raiz:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.yaml build backend
```

Evite publicar a saída de `docker compose config` sem `--quiet`, pois ela expõe
valores resolvidos das variáveis de ambiente.

## Migrations

Dentro de `backend/`, com PostgreSQL disponível e `backend/.env` configurado:

```powershell
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m alembic check
```

Não existem tabelas de negócio nem revisões nesta etapa. Alembic pode criar sua
tabela interna de controle. Não usamos `Base.metadata.create_all()`.
Quando modelos forem implementados, deverão ser importados em
`app/models/__init__.py`; as revisões geradas deverão ser revisadas antes de aplicar.

## Limites desta etapa

O Compose é local e não configura deploy, TLS ou backups na Hostinger.
CORS permite inicialmente `http://localhost:3000`, método GET e Content-Type,
sem credenciais. CORS não substitui autorização no backend.
As demais pastas estão preparadas, sem entidades, CRUDs ou regras de negócio.
