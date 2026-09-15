# Dia 14 — Relatório de infraestrutura e deploy

Data: 14 de setembro de 2026. **Nenhum deploy em VPS/Hostinger ou domínio público foi executado.** O código real, o stack sintético local e os comandos registrados abaixo são a fonte deste relatório.

## 1. Resumo, estado inicial e acesso

Branch `develop`, HEAD `67ee4c0` (Dia 13 já commitado antes desta etapa), Alembic `heads/current` local `20260913_10`. A suíte de referência era 404 testes. Havia apenas um arquivo não rastreado preexistente com nome incomum na raiz; foi preservado sem edição. Não havia host SSH, domínio, credencial de VPS ou configuração EasyPanel disponível no ambiente. Uma pergunta sobre acesso/domínio foi enviada; a preparação prosseguiu sem presumir resposta. Não houve commit, push, merge, release nem IA externa.

## 2. Arquitetura, Docker e persistência

Criado [compose.prod.yaml](../infra/compose.prod.yaml) separado do Compose local: Caddy expõe somente 80/443, frontend Next standalone e FastAPI ficam na rede `edge`, PostgreSQL fica na rede interna `data`; backend conecta às duas. Não há portas de DB/API/frontend publicadas no host. `postgres_prod_data`, `caddy_prod_data` e `caddy_prod_config` são volumes nomeados. Todos os serviços têm `restart: unless-stopped`, healthcheck de DB/API/Next e logs Docker rotacionados (10 MB × 5). Não há bind mount de código, reload, debug ou senha default. Imagens próprias recebem `DEPLOY_TAG` baseado no SHA aprovado; `frontend/Dockerfile` usa Node 24 e `npm ci`, gera standalone, copia apenas runtime/static/public. Backend continua com requirements fixados e usuário sem privilégios. `.dockerignore` de ambos exclui env, cache, testes/artefatos e dumps. Imagens externas estão tagueadas por versão/família; registrar digests no deploy real.

O stack sintético local criou banco isolado, aplicou Alembic e inseriu uma linha fictícia em `rate_limit_windows`. Após recriar o contêiner DB com o mesmo volume, a linha continuou presente (`count=1`). Isso valida persistência local, sem provar política de volume/backup da VPS. Ao terminar, os contêineres, redes, volumes e arquivo de env sintético foram removidos; o stack de desenvolvimento não foi alterado.

## 3. Migration, proxy, DNS, TLS e headers

Migration é comando único, manual e anterior à abertura do backend; não roda em cada réplica. No banco sintético, `upgrade head`, `current=20260913_10 (head)` e `check` sem operações passaram. Nenhuma migration nova foi criada; o HEAD permanece `20260913_10`. Em produção, backup/restore testado deve preceder upgrade. Rollback de schema não é automático.

[Caddyfile.prod](../infra/Caddyfile.prod) foi validado com domínios fictícios. Ele encaminha `app` ao Next e `api` ao FastAPI, preserva headers de aplicação, comprime e aplica HSTS inicial `max-age=86400` em HTTPS, sem `includeSubDomains`/preload. O Caddy gerencia certificado e redirect quando DNS/portas públicos existirem. Não houve emissão de certificado, resolução DNS real, validação de HTTPS público ou mixed content. O frontend usa `https://API_DOMAIN` no bundle; `APP_DOMAIN`/`API_DOMAIN` são variáveis, sem domínio final hardcoded.

Uvicorn confia **somente** no endereço estático `172.30.46.10` do Caddy na rede `172.30.46.0/24` para `X-Forwarded-For`/`X-Forwarded-Proto`. O Compose bloqueia acesso direto à API; Caddy, como primeiro proxy, ignora valores `X-Forwarded-*` arbitrários do cliente. Antes do deploy é preciso verificar ausência de conflito dessa subnet e observar IP real de clientes em HTTPS. Cloudflare não foi presumido; se adicionado, requer revisão explícita dos proxies confiáveis e proteção da origem. Headers de segurança e no-store do Dia 13 permanecem; Caddy acrescenta apenas HSTS, sem CSP concorrente.

## 4. Cookies, CORS, segredos, IA e rede

Configuração sintética de produção iniciou com `ENVIRONMENT=production`, `COOKIE_SECURE=true`, docs/OpenAPI off, CORS HTTPS explícito para `APP_DOMAIN`, `RATE_LIMIT_SECRET` estável e `AI_ENABLED=false`. `get_settings()` confirmou `production True False False True` para environment, cookie Secure, docs disponíveis, IA habilitada e comprimento suficiente do segredo. No backend local isolado, `/health` respondeu 200; `/docs` e `/openapi.json`, 404. Não foi feito login HTTPS real, portanto atributos `__Host-`, Secure/HttpOnly/SameSite/Path, Origin/CORS de navegador e HSTS público seguem sem confirmação operacional. Não existe `SESSION_SECRET` global: sessões são tokens opacos aleatórios cujo hash fica no banco.

`infra/.env.prod.example` exige senha PostgreSQL forte e segura para URL, HMAC secret 32+ caracteres, domínios, e-mail ACME e tag de commit. O arquivo preenchido deve ser 0600, ignorado pelo Git e protegido de operadores sem necessidade de acesso Docker. Somente URL pública entra em `NEXT_PUBLIC_*`; nenhum segredo foi adicionado ao frontend. Chave de IA não é configurada nem necessária com IA desativada. Política LGPD/IA e contrato com provedor permanecem decisões prévias à ativação externa.

O Compose não publica 5432/8000/3000. Firewall/SSH da VPS ainda não foram configurados: runbook orienta chave SSH, não bloquear acesso atual, portas 22/80/443 e verificação externa moderada. Sem VPS não houve scan externo, reboot, falha de upstream, medição de CPU/memória/disco ou validação de renovação TLS.

## 5. Backup, retenção e restore

Criados [backup-postgres.sh](../infra/scripts/backup-postgres.sh) e [verify-restore.sh](../infra/scripts/verify-restore.sh). O backup usa `pg_dump -Fc` em arquivo temporário no host fora do volume DB, verifica catálogo, grava SHA-256 e mantém provisoriamente cerca de 7 diários/4 semanais; agendamento diário por cron do host está no [runbook](backup-restore.md). O verificador cria banco temporário, confirma checksum quando presente, restaura com `--exit-on-error`, valida Alembic/contagem de users/ID sintético opcional e remove só o banco temporário. A sintaxe Bash dos dois scripts passou dentro de contêiner Linux. **Os scripts completos de host não foram executados no Windows**; o procedimento equivalente de dump/restore foi exercitado diretamente no PostgreSQL sintético.

Nesse teste direto, `pg_dump -Fc` → novo banco temporário → `pg_restore --exit-on-error` passou; Alembic restaurado era `20260913_10` e a linha fictícia conhecida estava presente (`count=1`). Banco temporário e dump foram removidos. Cópia criptografada fora da VPS, agendamento real, monitoramento de falha e restore dessa cópia seguem pendentes; a retenção não substitui decisão jurídica do controlador.

## 6. Rollback, operação e versionamento

[rollback.md](rollback.md) distingue troca de imagens anteriores quando schema compatível de recuperação de banco incompatível via backup verificado em destino novo. Exige SHA/tag/digest anterior, revisão Alembic e smoke; não usa `latest`, downgrade automático ou `down -v`. [deployment.md](deployment.md) traz comandos exatos de DNS, env, build, DB, Alembic, startup, health, logs, update e smoke. O stack local comprova ordem com DB healthy antes de backend e frontend healthy; recuperação pós-reboot/falha na VPS não foi testada. `docker compose logs`, `ps`, `docker system df` e `df -h` estão documentados para operação sem stack pesado de observabilidade.

## 7. Smoke funcional, visual e HTTPS pendentes

Não houve URLs públicas testadas. Não foram criadas contas MASTER/Professional/Student nesta etapa, nem smoke autenticado, transferência, console/Network, breakpoints 1366/1024/768/375 ou validação visual em ambiente HTTPS. Isso depende de domínio/VPS e contas sintéticas identificadas. O checklist de [deployment.md](deployment.md) cobre criação MASTER apenas se ausente, registro/aprovação Student, carteira Professional, planos, evolução, hidratação, reavaliação, informativos, notificações, AuditLog, transferência A→B com sessão antiga, IA desativada, 401/403/404 esperados, CORS/Origin, rate limit, no-store, headers e ausência de mixed content. Dados reais de cliente não foram usados. Não foi realizado teste de segurança externo/port scan da VPS.

## 8. Qualidade e validação local

Suíte backend completa: **404 passaram, nenhum pulado**, um aviso interno Starlette/AnyIO, em 9m17s. Ruff check/format, mypy strict (121 arquivos) e `pip check` passaram. Biome passou em 131 arquivos; TypeScript passou. O Docker build de produção executou `npm ci`, Next build/TypeScript e gerou imagem standalone; backend Docker build passou. Compose prod `config --quiet` e Caddy `validate` passaram com valores fictícios. Backend e Next containers ficaram healthy; banco/API/frontend sem portas no host. Alembic local e sintético: `20260913_10 (head)`, `check` limpo. O teste de backup/restore e persistência constam acima. Não houve alteração de schema ou dependências do produto. Os comandos e limites estão em [validation.md](validation.md).

## 9. Arquivos, problemas e bloqueios

Criados: `infra/compose.prod.yaml`, `infra/Caddyfile.prod`, `infra/.env.prod.example`, os dois scripts em `infra/scripts/`, `frontend/Dockerfile`, `frontend/.dockerignore`, `docs/deployment.md`, `docs/backup-restore.md`, `docs/rollback.md` e este relatório. Modificados: `.gitignore`, `backend/.dockerignore`, `frontend/next.config.ts`, README, architecture, validation, production-checklist e relatorio-contexto-proximos-prompts. O arquivo não rastreado preexistente da raiz foi preservado; não foi criado por esta etapa. Nenhum segredo real, certificado, dump ou screenshot temporário foi incluído no Git.

Problemas encontrados: Compose anterior era somente de desenvolvimento, sem frontend/proxy, HTTPS ou backup; foram criados arquivos separados. WSL/Bash do host Windows não ficou disponível para executar os scripts completos, então a sintaxe foi validada em Linux e o restore foi testado por comandos diretos equivalentes. Domínio/VPS/SSH não estavam disponíveis; portanto **deploy, DNS, certificado, firewall, backup externo e smoke autenticado de produção não foram executados**. Preparação para o Dia 15: obter ambiente e decisão de release, pin de digests externos, validar proxy IP/TLS, executar runbook/backup externo/restore, smoke completo e só então considerar abertura pública. O Dia 15 não foi iniciado.
