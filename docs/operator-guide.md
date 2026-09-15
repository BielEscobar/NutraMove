# Guia do operador técnico

Este guia resume as rotinas. O procedimento completo e os pré-requisitos estão em [deployment.md](deployment.md). Execute produção somente a partir de commit/tag aprovado, com `infra/.env.prod` protegido e sem working tree suja.

```bash
# Validar, construir e iniciar banco
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml config --quiet
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml build backend frontend
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml up -d --wait db

# Migration única e controlada
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic current
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic upgrade head
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic check

# Subir, consultar e parar sem apagar volumes
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml up -d --wait backend frontend proxy
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml ps
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml logs --tail=100 backend frontend proxy db
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml stop
```

Health público esperado: `https://<API_DOMAIN>/health` com status simples. `/docs` e `/openapi.json` devem retornar 404. Monitore também `df -h`, `docker system df`, falhas de backup e 5xx/429 anormais. Não registre corpos, cookies, tokens, prompts ou conteúdo clínico. Containers usam `restart: unless-stopped`; valide recuperação após reboot em janela segura.

Backup diário: `NUTRAMOVE_BACKUP_DIR=/srv/nutramove/backups bash infra/scripts/backup-postgres.sh`. Restore de teste: `bash infra/scripts/verify-restore.sh <arquivo.dump> [uuid-sintetico]`. Consulte [backup-restore.md](backup-restore.md); nunca restaure sobre o banco ativo e nunca use `down -v` em produção.

Para atualizar, registre SHA/tag/digests atuais, gere e valide backup, faça checkout limpo do commit aprovado, defina `DEPLOY_TAG`, construa imagens, execute Alembic uma vez, troque serviços e repita o smoke. Em falha siga [rollback.md](rollback.md). Não use somente `latest`.

Criar o primeiro MASTER somente se nenhum existir:

```bash
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml exec backend python -m app.cli.create_master
```

O comando é interativo; não registre senha. O operador precisa manter lista de responsáveis, acessos à VPS/DNS/backup, janela de manutenção, contato de incidente, RPO/RTO e evidências do [checklist de release](release-checklist.md).
