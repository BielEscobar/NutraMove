# Segurança — Dia 13

Este documento descreve controles técnicos existentes, não uma certificação de segurança ou aprovação de produção.

## Identidade, sessão e senha

Sessão opaca criada com `secrets.token_urlsafe(32)`; o banco guarda somente SHA-256 do token. Login sempre emite token novo e revoga o cookie anterior conhecido. Logout revoga a sessão; expiração, usuário inativo e papel alterado são verificados no banco. Senhas são hash Argon2 via pwdlib; inputs possuem máximo de 128 caracteres. Resposta de login inválido não distingue usuário inexistente de senha incorreta. Cookies são HttpOnly, SameSite=Lax, Path=/; em produção exigem Secure e prefixo `__Host-`.

## Origin, CORS e cache

Toda mutação autenticada passa por `get_current_user`, que exige Origin exata para POST/PATCH; login, logout e cadastro público também exigem Origin. GETs consultados não alteram estado. CORS admite apenas origins HTTP(S) explícitas, sem wildcard, com credenciais e métodos GET/POST/PATCH. Em produção, origins devem ser HTTPS e não loopback. Todas as respostas da API, inclusive erros e recursos privados, recebem `Cache-Control: no-store`. O frontend usa `fetch` com `cache: no-store` para a API.

## Rate limiting

`rate_limit_windows` no PostgreSQL usa `INSERT ... ON CONFLICT DO UPDATE` atômico. Limites: login 10 tentativas/5 minutos por endereço de rede; cadastro 5/hora por endereço; IA 10/hora por User Professional. Requisições excedentes recebem 429 e `Retry-After`. Tentativas falhas contam; operações comuns permanecem sem limite global. Identificadores são HMAC-SHA256 com `RATE_LIMIT_SECRET`; registros inativos há mais de dois dias são removidos oportunisticamente. Desenvolvimento gera segredo temporário, mas produção exige valor estável, aleatório e com 32+ caracteres compartilhado entre réplicas. Isso é proteção técnica, não quota comercial.

O backend usa apenas `request.client.host` e ignora `X-Forwarded-For` arbitrário. Atrás do reverse proxy do Dia 14, configurar a lista exata de IPs de proxy confiáveis no servidor ASGI e impedir acesso direto ao backend. Sem essa configuração, clientes podem compartilhar o endereço do proxy e o limite; não é seguro aceitar cabeçalho encaminhado de qualquer origem. Testar IP real observado após instalar proxy.

## Headers e documentação da API

API: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP apenas `frame-ancestors 'none'`, `Referrer-Policy: no-referrer`, `Permissions-Policy` para câmera/microfone/geolocalização desativados e no-store. O frontend recebe os headers equivalentes via Next config. CSP estrita de scripts foi adiada para análise com Next e reverse proxy; não se adicionou política que quebraria scripts do app. HSTS é emitido pela API apenas em requisição HTTPS de produção; no Dia 14 o proxy HTTPS deve impor HSTS. `DOCS_ENABLED` controla `/docs`, `/redoc` e `/openapi.json`: habilitados fora de produção e desabilitados por padrão em produção. `/health` retorna apenas status simples.

## Autorização e isolamento

O backend decide o acesso com User real da sessão e escopo SQL. Interface escondida não concede permissão.

| Recurso | Student | Professional | MASTER |
| --- | --- | --- | --- |
| Perfil, plano aprovado, evolução, hidratação, reavaliação, informativo | Próprios | Carteira atual; mutação segundo domínio | Leitura/administração prevista |
| Diet/Workout pendente e aprovação | Sem acesso | Cria/edita/aprova apenas na carteira e autoria permitida | Leitura administrativa, sem publicação |
| Assessment histórico após transferência | Consulta própria | Novo Professional lê, mas não edita autoria anterior | Leitura |
| Reevaluation | Cria/cancela pendente própria | Atende carteira atual | Leitura, sem resposta |
| Information | Publicados da carteira atual | Publica conteúdo próprio à carteira | Leitura |
| Notification | Inbox própria | Inbox própria | Somente inbox própria |
| Transferência e AuditLog | Sem acesso | Sem transferência | Transferência e consulta de log |
| NutraMove AI | Sem acesso | Geração para Student ACTIVE da carteira atual | Sem geração |

IDs de recursos de outra carteira retornam 404 quando a rota existe; role errada recebe 403; anônimo 401. O Professional novo pode ler plano histórico após transferência, mas não editar objeto do antigo. A transferência preserva AuditLog e histórico. Inputs Pydantic sensíveis proíbem campos extras; source/status/autor são definidos pelo servidor.

## Erros, logs e IA

Erros 401/403/404/409/422/429/502/503 preservam semântica. Erros inesperados retornam mensagem genérica; logs registram somente classe da exceção, sem traceback, payload, segredo ou caminho local. Uvicorn roda sem access log no contêiner local. Não usar logs de request body em proxy sem revisão de privacidade.

NutraMove AI fica desabilitado por padrão. Chave é `SecretStr` só no backend; provider usa HTTPS, timeout e `store=false`. Contexto é mínimo e explícito, validado novamente após retorno, com rechecagem de carteira sob lock. IA não publica nem notifica Student antes da aprovação. Orientações livres continuam sendo entrada não confiável: prompts subordinam a saída ao schema e o backend valida estrutura/escopo. Texto livre pode conter dados sensíveis; antes de produção é necessária decisão documentada sobre base legal, transparência, operador externo, transferência internacional e retenção. Nenhuma chave real deve estar no Git.

## Revisão restante antes de produção

Configurar proxy confiável, TLS/HSTS, segredos, backups/restore, firewall e retenção de dados conforme [checklist](production-checklist.md). Executar pentest independente e revisão de política clínica/privacidade conforme risco do serviço. Rate limiting por endereço atrás de NAT pode bloquear usuários legítimos; monitorar 429 sem registrar IP ou conteúdo bruto e ajustar limites com evidência. Este controle não substitui proteção anti-DDoS na borda.