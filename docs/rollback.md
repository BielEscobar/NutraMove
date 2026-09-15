# Rollback de implantação

Antes de cada atualização, registrar SHA anterior, tags/digests das imagens, revisão Alembic, backup verificado e hora de início. Decidir rollback se health, login, autorização, migration ou smoke crítico falhar; bloquear novas writes se houver risco à integridade. O procedimento depende do que mudou no banco.

## Aplicação sem reversão de schema

Se a migration nova é compatível com a imagem anterior, manter o banco e trocar `DEPLOY_TAG` em `infra/.env.prod` pelo tag anterior **já existente**. A execução deve ocorrer no mesmo código Compose/Caddyfile aprovado para aquela versão ou em checkout do commit anterior, sem working tree suja:

```bash
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml images
# Ajustar DEPLOY_TAG para <SHA_ANTERIOR> no arquivo protegido, após conferência.
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml up -d --no-build --wait backend frontend
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml ps
```

Repetir health, login sintético, CORS, cookie, dados privados e fluxos essenciais. Não reconstruir imagens antigas a partir de working tree nova nem usar `latest`. Se o frontend anterior usava outra URL pública, selecionar a imagem compilada para o mesmo domínio.

## Schema incompatível ou dados incorretos

Parar writes e avaliar com o responsável. `alembic downgrade` **não é rollback universal**: migrations podem remover colunas/tabelas e perder dados. Confirmar arquivo de migration, dependências, alterações após o backup e estratégia de reconciliação. Preferir banco novo restaurado do backup verificado e troca controlada de `DATABASE_URL`/volume, preservando o banco com falha para análise. Nunca rodar restore por cima do banco ativo. Ao voltar imagem e banco ao mesmo ponto, repetir smoke completo e registrar perda de dados/RPO real. Não usar `docker compose down -v`.

Se certificado/proxy falhar, restaurar Caddyfile/imagem anterior e validar domínio, DNS, 80/443 e HTTPS sem desativar proteção por conveniência. Se o problema for só `RATE_LIMIT_SECRET`, não trocar sem entender janelas existentes: a rotação faz chaves anteriores deixarem de contar. Registrar incidente, mudança e decisão de reabertura. [Deployment](deployment.md) e [backup/restore](backup-restore.md) são as instruções complementares.
