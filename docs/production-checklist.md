# Preparação operacional — Dia 14 (sem deploy neste Dia)

Este checklist é uma lista de decisões e verificações para futura implantação na Hostinger VPS. Marcar itens somente com evidência de execução.

- [ ] Definir responsáveis, domínio, DNS e política de privacidade/termos, inclusive tratamento por IA externa; manter `AI_ENABLED=false` até aprovação documentada.
- [ ] Atualizar VPS, acesso SSH com chave, usuários de privilégio mínimo, firewall permitindo somente SSH restrito e HTTP/HTTPS ao reverse proxy; PostgreSQL e backend não devem ficar públicos.
- [ ] Instalar Docker/Compose suportados, definir restart policy, limites de recursos, volumes persistentes e versão/imagem imutável do PostgreSQL e das aplicações.
- [ ] Guardar `DATABASE_URL`/POSTGRES_PASSWORD, `RATE_LIMIT_SECRET` (32+ caracteres estáveis e compartilhados), eventual `AI_API_KEY` e demais segredos fora do Git, com permissões restritas e plano de rotação.
- [ ] Configurar `ENVIRONMENT=production`, `COOKIE_SECURE=true`, CORS HTTPS explícito, `DOCS_ENABLED=false` salvo decisão consciente, URL pública correta do frontend e AI desabilitada por padrão.
- [ ] Configurar reverse proxy (Nginx/Caddy/Cloudflare se adotado), TLS válido, renovação de certificado, redirecionamento HTTP→HTTPS, HSTS na borda após teste e limites de tamanho/tempo de requisição compatíveis com IA.
- [ ] Definir exatamente os IPs de proxy confiáveis no Uvicorn/ASGI; bloquear acesso direto ao backend; confirmar que `request.client.host` é o cliente real para rate limiting sem aceitar `X-Forwarded-For` arbitrário.
- [ ] Validar headers de segurança do frontend, API e proxy; ajustar CSP completa somente após teste do Next.js em produção.
- [ ] Criar backup PostgreSQL automatizado, criptografado e fora do host principal, com retenção, acesso mínimo, restauração testada e monitoramento de falha. Proteger também volumes e segredos.
- [ ] Fazer migration `alembic upgrade head` em janela planejada antes de ativar backend; confirmar `current` e `check`, com backup e plano de rollback. Não editar migrations históricas.
- [ ] Preparar deploy e rollback de frontend/backend por versão, healthcheck/liveness, logs sem payloads sensíveis, restart policy e alertas essenciais (5xx, 429 anormal, banco, disco, backup).
- [ ] Definir limpeza operacional de `rate_limit_windows` inativos se não houver tráfego e política de retenção/encerramento para dados de saúde, histórico, AuditLog e backups.
- [ ] Smoke test HTTPS com contas sintéticas e perfis Student/Professional/MASTER: login/logout, Origin, CORS, planos, transferência, notificações e, se autorizado, IA com dados sintéticos.
- [ ] Revisar acessibilidade/responsividade e executar teste de restore antes de abrir acesso real; registrar responsáveis e evidências.

Nenhum item deste checklist representa implantação já realizada.

## Evidência local do Dia 14

- [x] Compose de produção com redes separadas, volumes e healthchecks validado com variáveis sintéticas; backend/frontend Docker build passaram.
- [x] Caddyfile validado em contêiner sem solicitar certificado real.
- [x] PostgreSQL isolado manteve dado sintético após recriação do contêiner; migration 20260913_10, dump e restore em banco temporário conferidos.
- [x] Backend de produção sintético: health 200, docs/OpenAPI 404, Secure configurado, IA desativada; Next standalone healthy. DB/API/frontend sem portas publicadas no host.
- [ ] DNS/HTTPS real, IP real através do proxy, firewall/SSH da VPS, backup externo e smoke autenticado dos perfis: dependem do ambiente Hostinger e de domínios/credenciais operacionais ainda não disponíveis.

Runbooks: [deployment.md](deployment.md), [backup-restore.md](backup-restore.md) e [rollback.md](rollback.md). Esses checks locais não aprovam abertura a usuários reais.
