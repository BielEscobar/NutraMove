# Arquivos da etapa de autenticação

## Criados

- backend/app/models/user.py: usuário e enum de roles.
- backend/app/models/auth_session.py: sessões revogáveis.
- backend/app/core/security.py: Argon2 e digest de tokens.
- backend/app/schemas/auth.py: contratos de login, resposta e criação administrativa.
- backend/app/repositories/users.py e auth_sessions.py: consultas.
- backend/app/services/auth.py: login, logout e criação de MASTER.
- backend/app/api/auth.py e dependencies.py: rotas e permissões.
- backend/app/cli/__init__.py e create_master.py: comando administrativo.
- backend/alembic/versions/20260910_01_users_sessions.py: migration inicial.
- backend/tests/test_auth.py e test_auth_config.py: testes de autenticação e configuração.
- frontend/src/lib/api.ts: cliente HTTP com cookies.
- frontend/src/app/login/page.tsx e account/page.tsx: entrada e conta.
- frontend/src/app/fonts/Inter.ttf e OFL.txt: fonte local e licença.
- docs/authentication.md e este inventário: decisões e arquivos.

## Modificados

- backend/app/main.py: registro de rotas e CORS com credenciais.
- backend/app/core/config.py: duração de sessão, cookie seguro e validações.
- backend/app/db/session.py: timeout explícito de conexão.
- backend/app/models/__init__.py: registro dos modelos para Alembic.
- backend/alembic/env.py: suporte a conexão fornecida pelos testes em schema isolado.
- backend/requirements.txt: pwdlib[argon2] e email-validator, versões fixadas.
- backend/.env.example: configuração da sessão.
- frontend/src/app/layout.tsx: Inter local e metadados.
- frontend/src/app/globals.css: identidade visual NUTRAMOVE e campos do formulário.
- frontend/src/app/page.tsx: entrada pelo login.
- README.md, docs/architecture.md e docs/validation.md: instruções e resultados atuais.

Não havia autenticação anterior para substituir. Nenhuma migration previamente
aplicada foi editada. Não houve commit automático.
