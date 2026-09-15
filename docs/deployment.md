# Implantação V1 em VPS — execução manual controlada

Estado: **preparado e validado localmente; não executado na Hostinger**. Não há domínio, SSH ou VPS acessível registrado no repositório. Este runbook pressupõe uma VPS Linux com Docker Engine/Compose, DNS sob controle do operador e um commit aprovado. A arquitetura é DNS → Caddy (80/443) → Next.js (`app`) e FastAPI (`api`) → PostgreSQL em rede interna. [Compose de produção](../infra/compose.prod.yaml) não substitui o Compose local de desenvolvimento.

## Pré-requisitos e DNS

1. Criar registros A `app` e `api` apontando para o IPv4 público da VPS. Se houver IPv6, criar AAAA apenas se o firewall e o proxy aceitarem IPv6. Não assumir Cloudflare; se usado, iniciar em DNS-only e definir política de proxy confiável separadamente antes de ativar proxy/CDN.
   Se a Hostinger/EasyPanel já fornecer TLS e proxy gerenciado, não iniciar o serviço `proxy` deste Compose em paralelo; adaptar o encaminhamento e a lista de IPs confiáveis, depois repetir todos os testes.
2. Preparar SSH por chave, usuário operacional com permissão Docker, atualizações de segurança e firewall. Validar acesso SSH antes de alterar regras. Permitir 22/tcp (preferencialmente restrito), 80/tcp e 443/tcp. Não publicar 5432, 8000 ou 3000. Conferir `ss -tulpn`, painel Hostinger e `docker compose ps`.
3. Verificar que `172.30.46.0/24` não conflita com redes Docker/VPS existentes. O Caddy usa `172.30.46.10` na rede `edge`; **somente esse IP** é confiável para Uvicorn. Se for necessário mudar a subnet, alterar em conjunto Compose e `--forwarded-allow-ips`, e repetir o teste de IP/HTTPS. O Caddy padrão ignora `X-Forwarded-For` fornecido pelo cliente e estabelece os headers encaminhados; não configurar `trusted_proxies` de CDN sem faixas oficiais e proteção do origin.
4. Reservar espaço persistente para `nutramove-prod_postgres_prod_data`, `nutramove-prod_caddy_prod_data` e `nutramove-prod_caddy_prod_config`, além de armazenamento de backup fora do volume do banco e cópia externa criptografada. Validar `df -h` e `docker system df`.

## Código, variáveis e build

Usar apenas um commit conhecido e revisado; `develop` pode servir para staging, mas produção pública depende da decisão de release. No host, nunca editar código diretamente nem implantar working tree suja:

```bash
git fetch --all --tags
git checkout <SHA_APROVADO>
git status --short
git rev-parse HEAD
cp infra/.env.prod.example infra/.env.prod
chmod 600 infra/.env.prod
```

Preencher `infra/.env.prod` com domínios reais sem esquema (`APP_DOMAIN`, `API_DOMAIN`), e-mail ACME, `DEPLOY_TAG=<SHA_APROVADO>`, senha PostgreSQL **aleatória e segura para URL** e `RATE_LIMIT_SECRET` aleatório de pelo menos 32 caracteres. Não usar exemplos. O banco e o HMAC usam esses valores no runtime; somente `https://API_DOMAIN` entra no build público do Next. `AI_ENABLED=false` permanece no Compose; chave de IA não é necessária. Não colocar segredos em `NEXT_PUBLIC_*`, imagem, log ou Git. O operador com acesso ao Docker pode inspecionar variáveis de contêiner; limitar acesso ao socket Docker e ao arquivo `.env.prod`. Para produção com gestor de segredos, adaptar a injeção sem alterar o contrato do backend.

```bash
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml config --quiet
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml build backend frontend
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml up -d --wait db
```

`frontend/Dockerfile` usa `npm ci` e `output: standalone`; `backend/Dockerfile` instala requirements fixados. As imagens próprias têm tag `DEPLOY_TAG`. Guardar commit, tags e digests das imagens externas usados em cada implantação. Não fazer atualização de imagem base no mesmo ato sem regressão.

## Backup, migration e startup

Antes de atualizar banco já usado, fazer backup e restore de verificação conforme [backup-restore.md](backup-restore.md). Em banco novo, registrar que não existe estado anterior. **Uma única execução de Alembic** deve ocorrer antes de iniciar a API pública:

```bash
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic heads
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic current
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic upgrade head
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic current
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml run --rm --no-deps backend python -m alembic check
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml up -d --wait backend frontend proxy
```

Não iniciar instâncias concorrentes de migration; não usar downgrade automático. `db` precisa estar healthy, backend/Next também possuem healthcheck. `restart: unless-stopped` cobre reinício do host. O Caddy adquire/renova certificados e redireciona HTTP para HTTPS quando os nomes públicos e portas 80/443 funcionam. HSTS inicial na borda é `max-age=86400`, sem `includeSubDomains` ou preload. O proxy preserva headers de API/Next e não define CSP conflitante.

## Smoke de abertura

Executar por HTTPS, de rede externa à VPS, com certificado válido e sem `-k`:

```bash
curl -I http://app.<dominio>              # esperar redirect HTTPS
curl -I https://app.<dominio>/login     # esperar 200 e HSTS
curl -fsS https://api.<dominio>/health # esperar {"status":"ok"}
curl -i https://api.<dominio>/docs     # esperar 404
curl -i https://api.<dominio>/openapi.json # esperar 404
```

Conferir certificado/hostname/renovação, `Secure; HttpOnly; SameSite=Lax; Path=/` e nome `__Host-` no cookie de login, CORS somente do app real, Origin falsa bloqueada, no-store em dados privados, ausência de mixed content e IP de cliente observado no limite (sem registrar IP bruto). Testar 429 de modo controlado com conta sintética e janela de recuperação. `AI_ENABLED=false` deve resultar em estado indisponível apropriado; não fazer chamada paga. Criar MASTER via CLI interativa **somente se não existir**, `docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml exec backend python -m app.cli.create_master`; não registrar senha.

Depois, usar contas fictícias identificadas para smoke de MASTER (profissionais, alunos, transferência, AuditLog), Professional (carteira, Diet/Workout, Assessment, Hydration, Reevaluation, Information, Notification, IA desativada) e Student (registro/pendência/aprovação, dashboard, planos, evolução, hidratação, reavaliação, informativos, inbox, logout). Conferir transferência A→B com sessões antigas, console e Network do navegador, e layouts 1366/1024/768/375. Desativar/remover contas fictícias conforme política aprovada. **Esses smokes não foram executados em produção neste Dia.**

## Operação e atualização

```bash
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml ps
docker compose --env-file infra/.env.prod -f infra/compose.prod.yaml logs --tail=100 backend frontend proxy db
docker system df
df -h
```

Logs Docker têm rotação de 10 MB × 5 por serviço; não habilitar access log com headers/cookies ou payloads. Verificar backups, espaço, 5xx, 429 anormal e health diariamente. Uma parada planejada de backend/frontend deve retornar erro previsível no proxy e recuperar ao reiniciar; testar somente em janela segura. Para atualizar, registrar o SHA anterior, fazer backup + restore test, compilar imagens com novo SHA, executar Alembic uma vez, trocar serviços e repetir smoke. Em falha, seguir [rollback.md](rollback.md). Não usar `docker compose down -v` em produção.

Referências de configuração: [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [HTTPS automático](https://caddyserver.com/docs/automatic-https), [Next self-hosting](https://nextjs.org/docs/app/guides/self-hosting) e [Compose em produção](https://docs.docker.com/compose/how-tos/production/).
