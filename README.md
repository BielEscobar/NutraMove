# NutraMove

NutraMove é uma aplicação web para acompanhamento de nutrição e treino. A V1 separa as áreas de MASTER, Professional e Student e inclui gestão de carteira, dietas, treinos, avaliações e evolução, hidratação, reavaliações, informativos, notificações, transferência com auditoria e geração opcional de rascunhos por IA.

O frontend usa Next.js, React e TypeScript. A API usa FastAPI, SQLAlchemy, Pydantic e Alembic sobre PostgreSQL. O ambiente de produção preparado usa containers Docker, frontend Next standalone e Caddy como proxy HTTPS. A IA fica desabilitada por padrão.

## Requisitos

- Node.js 24 e npm;
- Python 3.13;
- Docker com Docker Compose;
- PostgreSQL 17 pelo Compose.

## Desenvolvimento local

Copie os arquivos de exemplo e substitua os placeholders locais:

```powershell
if (!(Test-Path infra/.env)) { Copy-Item infra/.env.example infra/.env }
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (!(Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d --wait
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic upgrade head
```

Frontend em modo de desenvolvimento:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Acesse `http://localhost:3000`. A API e o health local ficam em `http://localhost:8000` e `http://localhost:8000/health`. Crie o primeiro MASTER pelo comando interativo:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m app.cli.create_master
```

Não há usuário ou senha padrão. Sessões usam cookie HttpOnly; segredos não devem entrar em variáveis `NEXT_PUBLIC_*`.

## Testes e qualidade

No diretório `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pip check
```

No diretório `frontend`:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd audit --omit=dev --audit-level=high
```

## Produção

O stack está em `infra/compose.prod.yaml`. Ele expõe apenas Caddy nas portas 80/443; banco, API e frontend permanecem internos. O deploy público ainda exige VPS, DNS, segredos, TLS, backup externo e smoke no domínio real.

Use o [guia de deploy](docs/deployment.md), o [guia do operador](docs/operator-guide.md), os procedimentos de [backup e restore](docs/backup-restore.md) e [rollback](docs/rollback.md). Nunca use `down -v` em produção nem restaure sobre o banco ativo.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Validação](docs/validation.md)
- [Segurança](docs/security.md) e [privacidade/LGPD](docs/privacy-lgpd.md)
- [Entrega ao cliente](docs/client-handover.md)
- [Checklist de release](docs/release-checklist.md)
- [Relatório final da V1](docs/dia15-relatorio-final.md)
- [Changelog](CHANGELOG.md)
