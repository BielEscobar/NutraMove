# Dia 13 — Relatório de hardening e validação

Data: 14 de setembro de 2026. O código e os comandos executados nesta etapa são a fonte deste relatório; os números finais de validação constam também em [validation.md](validation.md).

## 1. Resumo e estado inicial

Branch `develop` limpa no início, sem mudanças locais a preservar. Alembic `heads` e banco local em `20260913_09`; referência anterior: 397 testes. A revisão cobriu backend, frontend, infra, testes e documentação dos Dias 1–12. Nenhum commit, push, deploy ou chamada paga de IA foi feito.

## 2. Achados e correções

Foram confirmadas três lacunas transversais: ausência de limite de tentativas em login, cadastro e IA; ausência de headers de segurança consistentes; e documentação da API aberta por padrão mesmo em produção. Também havia registro de localização de traceback em erro inesperado, expondo caminho local no log, e o frontend não tinha mensagem própria para 429. Corrigidos com limite por endpoint no PostgreSQL, middleware de headers, política configurável de docs, log reduzido à classe da exceção e mensagens de espera no cliente. Uma captura mobile inicial foi recortada pelo limite de largura do Chrome headless; a medição posterior com viewport emulado confirmou ausência de overflow no login em 375 px, sem alteração de layout.

## 3. Autenticação, sessões, cookies e senhas

Sessão opaca de alta entropia; somente hash SHA-256 do token é persistido. Login emite token novo, logout revoga, expiração e usuário inativo são recusados. Status e papel são consultados no banco, inclusive desativação de Professional/Student. Cookies HttpOnly, SameSite=Lax e Path=/; produção exige Secure e prefixo `__Host-`. Senhas usam Argon2, limite de comprimento e confirmação nos fluxos aplicáveis; hash e texto puro não saem por schema, AuditLog ou log. Login inválido não diferencia e-mail inexistente de senha errada. Testes existentes cobrem fixation, expiração e revogação; não houve mudança desse contrato.

## 4. Rate limiting, Origin, CORS, headers e cache

Login: 10 tentativas por 5 minutos por endereço observado pelo ASGI. Cadastro Student: 5 por hora por endereço. IA: 10 por hora por User Professional. `INSERT ... ON CONFLICT` atômico compartilha estado no PostgreSQL; identificador é HMAC-SHA256 com segredo configurável, sem IP bruto. Excesso retorna 429 e `Retry-After`; falhas contam e a janela reinicia. Não existe limite global. `X-Forwarded-For` arbitrário é ignorado; o proxy confiável e isolamento do backend devem ser configurados no Dia 14.

Mutations autenticadas passam pela proteção de Origin na dependência de sessão; login, logout e registro público também exigem Origin. CORS permanece restrito a origins explícitas, com credentials e métodos necessários; produção rejeita HTTP e loopback. API e frontend recebem nosniff, proteção contra frame, política de referrer e permissions. CSP limita `frame-ancestors`; CSP estrita de scripts depende de teste conjunto com Next/proxy. HSTS só em HTTPS de produção na API e deve ser imposto na borda no Dia 14. Toda resposta da API recebe `Cache-Control: no-store`, inclusive 4xx/5xx; `fetch` privado do frontend também usa no-store.

## 5. RBAC, IDOR/BOLA e mass assignment

Auditoria de rotas e testes existentes confirma escopo no backend para Student próprio, carteira atual de Professional e atribuições administrativas MASTER. IDs alheios seguem 404, papel inadequado 403, ausência de sessão 401. MASTER não gera IA, não atende Reevaluation, não aprova plano clínico e só lê a própria inbox. Inputs sensíveis rejeitam campos extras; role, vínculos, status, autoria, origem, leitura de Notification e AuditLog vêm da sessão ou serviço. Matriz de domínio e autorização está em [security.md](security.md).

## 6. Revisão por domínio e transferência

Diet/Workout preservam versionamento, aprovação e origem `AI_GENERATED`/`PENDING_REVIEW`; publicação e Notification seguem aprovação explícita. Assessment e Evolution mantêm autoria e histórico. Hydration agrega no PostgreSQL e usa carteira atual. Reevaluation preserva uma aberta por Student e transições válidas. Information respeita audiência publicada e carteira atual. Notification é inbox do User, sem acesso administrativo a caixas alheias. AuditLog registra transferência e não recebe senha/token. Após transferência A→B, A perde carteira, B ganha leitura do histórico e não pode editar autoria clínica antiga; Information antiga segue a regra existente; `IN_REVIEW` bloqueia transferência. A suíte existente reexecuta isolamento, concorrência e essas políticas.

## 7. SQL, XSS, paginação, erros e logs

Busca por SQL interpolado com input, ORDER BY arbitrário e uso de `dangerouslySetInnerHTML` não encontrou caminho vulnerável. Consultas usam SQLAlchemy parametrizado; listas têm limites e paginação existentes. Texto livre aparece como texto React. Erros mantêm 400/401/403/404/409/422/429/502/503; falha inesperada devolve mensagem genérica. Logs de aplicação registram somente classe da exceção inesperada, sem traceback/caminho, corpo, prompt ou resposta do provedor. Proxy e ferramentas operacionais devem manter essa política.

## 8. NutraMove AI e privacidade

`AI_ENABLED=false` permanece padrão. Chave `SecretStr` fica só no backend; provider isolado, HTTPS, timeout, `store=false`, saída estruturada e validação Pydantic. Contexto é mínimo, Student ACTIVE e carteira são rechecados sob lock após chamada externa. Instruções livres são entrada não confiável; schema e validação do backend continuam sendo a barreira. IA cria rascunho, nunca publica ou notifica Student antes da aprovação. Testes usam fake provider, sem crédito externo. Dados livres podem conter informação sensível; governança, base legal, transparência e contrato com provedor precisam de decisão antes de habilitar IA em produção.

## 9. LGPD, configuração e segredos

[privacy-lgpd.md](privacy-lgpd.md) inventaria categorias, finalidade técnica, acesso, transferência, IA, retenção, direitos e backups, sem dados reais nem conclusão jurídica automática. `ENVIRONMENT=production` exige cookie Secure, CORS HTTPS não local, segredo estável de rate limit e chave de IA quando habilitada. `/docs`, `/redoc` e `/openapi.json` ficam desabilitados por padrão em produção, com opção explícita de habilitar. `/health` responde status simples. Variáveis de exemplo não contêm credenciais reais. Retenção, anonimização/exclusão, incidentes, backups e tratamento de dados de saúde exigem política do controlador; nenhuma exclusão geral foi implementada.

## 10. Migration e testes novos

Migration `20260913_10` depende de `20260913_09` e cria `rate_limit_windows` com PK hash, janela, contagem positiva e índice de limpeza. Não foram alteradas migrations antigas. Testes novos cobrem reset e 429, login/cadastro, limite de IA, headers em sucesso/erro, configuração de produção/docs/HSTS e log sanitizado. Testes antigos permanecem sem skip. O total final e a validação de upgrade/roundtrip constam na seção de validação abaixo.

## 11. Validação, navegador e acessibilidade

Os testes backend usam API real e PostgreSQL em schemas temporários, com autenticação, perfis, publicação, transferência e IA fake. Chrome headless real abriu o login e o estado de erro de sessão em 1366, 1024, 768 e 375 px. A largura foi medida via DevTools Protocol: `scrollWidth` 1366/1024/753/375 para viewports 1366/1024/768/375, respectivamente; não houve overflow horizontal. Capturas representativas foram inspecionadas; o mobile de 375 px foi repetido no build final sem mudança de layout. A primeira captura CLI em 375 px era um recorte do viewport mínimo interno do Chrome, não um defeito da página. Não foram executados login autenticado no navegador nem os fluxos visuais completos de Student, Professional e MASTER; a dívida visual dos Dias 10–12 permanece. Não há Playwright no projeto; não foi criada suíte E2E persistente. Revisão estática encontrou labels, estados de loading/erro/vazio, controles de submissão e texto alternativo dos gráficos existentes; isso não equivale a auditoria WCAG. Não houve uso de contas ou dados reais para capturas.

## 12. Dependências, desempenho e operação

`pip check` aprovado; `npm audit --omit=dev --audit-level=high` encontrou zero vulnerabilidades no conjunto auditado. Não houve atualização major. Limite usa índice e SQL atômico; dashboards, contagem de Notification, agregação Hydration e contexto de IA mantêm consultas existentes. Limpeza de janelas antigas é oportunista, sem cron; confirmar retenção operacional no Dia 14. [production-checklist.md](production-checklist.md) detalha VPS Hostinger, Docker, PostgreSQL, TLS, proxy, segredo, migration, backup/restore, health, logs, firewall, rollback e smoke. Sem deploy.

## 13. Resultado final e débitos

Suíte completa: **404 passaram, nenhum pulado**, em 8m03s; sete testes novos. A primeira execução apontou uma expectativa antiga de log com nome de função; a expectativa foi atualizada para a política de log sanitizado e a suíte completa passou. Permanece um `DeprecationWarning` interno Starlette/AnyIO. Ruff check e format --check aprovados; mypy strict aprovou 121 arquivos; `pip check` sem incompatibilidades. Biome aprovou 131 arquivos; TypeScript e Next build aprovados. Compose config, Docker build backend e `/health` local (200) aprovados. Alembic local está em `20260913_10 (head)` e `check` não encontrou novas operações; testes em schemas descartáveis executaram downgrade/upgrade. O primeiro Docker build falhou por acesso do sandbox ao contexto e foi repetido com permissão; o primeiro rebuild Next após as capturas encontrou arquivo `.next` bloqueado pelo OneDrive e passou após remover somente o cache gerado, com caminho verificado. Arquivos temporários do Chrome foram removidos. `git diff --check` aprovado.

Permanecem antes da produção: configuração e teste do proxy confiável, TLS/HSTS na borda, segredos, backup/restore, política LGPD/IA aprovada, revisão visual autenticada completa dos Dias 10–12, E2E persistente e teste de segurança independente. O Dia 14 não foi iniciado.
