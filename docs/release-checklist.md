# Checklist de release V1

Itens locais confirmados em 15 de setembro de 2026:

- [x] Suíte backend completa (404 testes, nenhum skip)
- [x] Ruff check e format, mypy strict e pip check
- [x] Biome, TypeScript e Next production build
- [x] Docker backend/frontend e Compose de produção
- [x] Alembic current/head/check em `20260913_10`
- [x] Caddyfile validado com domínios fictícios
- [x] Persistência em volume e restore em banco temporário sintético
- [x] RBAC/IDOR, fluxos V1, transferência, segurança e IA fake cobertos pela regressão automatizada
- [x] Visual autenticado local em 112 combinações de rota/perfil/largura, inclusive mobile 375 px
- [x] Console local sem exceção JavaScript; somente abortos esperados da navegação automatizada
- [x] Segredos e artefatos locais revisados; ajuda acidental do `less` removida
- [x] README, handover, operação, deploy, backup/restore, rollback e changelog

Itens que exigem a release/ambiente público e continuam pendentes:

- [ ] Commit do Dia 14/15 revisado em `develop`
- [ ] Merge aprovado de `develop` para `main`
- [ ] Tag assinada/anotada `v1.0.0` no commit aprovado
- [ ] Segredos reais instalados fora do Git
- [ ] VPS, firewall e SSH validados
- [ ] DNS real de app/API
- [ ] TLS válido, redirect HTTP→HTTPS e renovação
- [ ] IP real do cliente confirmado através do proxy confiável
- [ ] Backup diário e cópia externa criptografada configurados
- [ ] Restore testado a partir da cópia externa
- [ ] Smoke MASTER em HTTPS
- [ ] Smoke Professional em HTTPS
- [ ] Smoke Student em HTTPS
- [ ] Transferência A→B e AuditLog em HTTPS com dados fictícios
- [ ] Cookie, CORS/Origin, rate limiting, no-store e docs off no domínio real
- [ ] Visual autenticado no ambiente HTTPS em 1366/1024/768/375
- [ ] Console/Network do ambiente HTTPS sem erro inesperado ou mixed content
- [ ] Contas fictícias de homologação removidas/desativadas
- [ ] Cliente recebeu acessos por canal seguro, guia e responsáveis
- [ ] Checklist pós-deploy acompanhado nas primeiras 24 horas

Pós-deploy: verificar `ps`/health, certificado, login/logout dos três papéis, páginas críticas, backup agendado, espaço/logs, restart seguro e alertas essenciais; registrar versão/digests, hora, operador, resultado e eventual rollback sem dados pessoais.
