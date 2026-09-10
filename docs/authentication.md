# Autenticação — base necessária para o Dia 3

## Escopo

O checkout inicial não continha autenticação, apesar do nome do commit mencionar
Dias 1 e 2. Após autorização, foi implementada esta etapa de autenticação.
O módulo MASTER de gestão de profissionais continua sendo a próxima etapa.
Nenhuma entidade Professional ou Student foi criada.

## Modelo de dados

users contém UUID, nome, e-mail, password_hash, role, is_active e timestamps UTC.
O e-mail é normalizado para minúsculas e protegido por UNIQUE e CHECK no PostgreSQL.
As roles MASTER, PROFESSIONAL e STUDENT são valores de um enum com constraint no
banco. Isso prepara autorização futura sem criar as entidades de negócio.

auth_sessions contém hash do token, user_id, criação e expiração, com chave
estrangeira para users e índices por usuário e expiração.
A migration é 20260910_01_users_sessions.py.

## Login e sessão

- Senhas usam Argon2 por meio de pwdlib; não são armazenadas em texto puro.
- O login recebe somente email e password. Campos extras são rejeitados.
- E-mail inexistente, senha incorreta e usuário inativo retornam a mesma mensagem 401.
- O token é aleatório, gerado com secrets.token_urlsafe(32). Somente seu digest
  SHA-256 é persistido. Não é um JWT e não contém role ou dados pessoais.
- O cookie é HttpOnly, SameSite=Lax, com duração padrão de uma hora.
- Em HTTPS, COOKIE_SECURE=true ativa Secure e o prefixo __Host-.
- O login troca a sessão anterior daquele navegador. Logout revoga a sessão no banco
  e remove o cookie. Uma cópia de um token revogado também deixa de funcionar.
- Cada requisição protegida consulta sessão, expiração, usuário ativo e role no banco.
- Expiração é absoluta; não há refresh token ou renovação automática.
- Sessões expiradas do usuário são removidas ao fazer novo login.

## Endpoints

| Método | Caminho | Comportamento |
| --- | --- | --- |
| POST | /auth/login | Valida credenciais, cria sessão e retorna os dados públicos do usuário. |
| GET | /auth/me | Retorna o usuário autenticado; sem sessão válida retorna 401. |
| POST | /auth/logout | Revoga a sessão e responde 204; é idempotente. |

As respostas públicas não incluem password_hash nem token. O token vai somente no
cookie HttpOnly. Respostas de sucesso da autenticação usam Cache-Control: no-store.

get_current_user é a dependência de identidade.
require_roles(UserRole.MASTER) protege os futuros endpoints administrativos:
usuário sem sessão recebe 401; PROFESSIONAL e STUDENT recebem 403.
Nenhuma role, user_id ou cabeçalho de autorização inventado pelo frontend decide
permissão no servidor.

## CSRF e CORS

CORS permite credenciais, origens explícitas, GET/POST e Content-Type.
POST /auth/login e POST /auth/logout exigem Origin presente em CORS_ORIGINS.
get_current_user também exige origem confiável em métodos que alteram dados.

Isso protege os fluxos por cookie contra requisições de outras origens. CORS sozinho
não fornece autorização nem substitui essa verificação.
Clientes HTTP de teste devem enviar Origin: http://localhost:3000. O Swagger na
origem da API não está autorizado por padrão para POST; configure uma origem adicional
explicitamente se precisar usar esses comandos pela documentação interativa.

O frontend usa fetch com credentials: include e não persiste tokens em localStorage.
A implantação deve manter frontend e API no mesmo site, como app.exemplo.com e
api.exemplo.com, com HTTPS. Domínios de sites diferentes exigem outra análise da
política de cookies; não altere SameSite sem revisar a proteção CSRF.

## Criar o primeiro MASTER

Na raiz do repositório, após subir o Compose e aplicar a migration:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m app.cli.create_master
```

Ou, dentro de backend/, usando o banco local configurado:

```powershell
.venv/Scripts/python.exe -m app.cli.create_master
```

O comando solicita nome, e-mail e senha com confirmação. A senha deve ter de 12 a
128 caracteres e não aparece no terminal nem nos argumentos do processo.
A role é fixada como MASTER pelo comando, sem parâmetro para o frontend.

Nenhuma conta padrão foi criada. O comando é uma operação administrativa para quem
já tem acesso ao servidor; não existe endpoint público de cadastro.

## Frontend

/ redireciona para /login.
/login verifica sessão existente, mostra formulário, loading e erros.
/account consulta /auth/me e exibe nome, e-mail, perfil e logout.
O redirecionamento do frontend melhora a navegação; a proteção dos dados está no backend.

A fonte Inter é servida localmente por next/font/local, com licença OFL incluída.
A interface usa a paleta NUTRAMOVE. Não há dashboard administrativo, gestão de
profissionais, alunos ou IA nesta entrega.

## Verificações

Os testes de autenticação usam PostgreSQL configurado em backend/.env, mas criam um
schema aleatório test_auth_* separado. Aplicam a migration real e verificam upgrade,
downgrade e correspondência com os modelos. Cada teste usa transação com rollback.
O schema temporário é removido ao final. Não se usa SQLite nem create_all.

Os testes antigos da fundação continuam isolados do banco. Para rodar toda a suíte,
PostgreSQL deve estar ativo e o usuário configurado deve poder criar schemas:

```powershell
cd backend
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
```

A opção no:cacheprovider evita um problema local de permissão no cache do pytest;
nenhum teste ou aviso de código é desabilitado.

## Limites e débitos técnicos

- Antes de exposição pública: configurar limitação de tentativas de login e
  observabilidade, além de HTTPS e configuração de produção.
- Recuperação/troca de senha, MFA e revogação de todas as sessões por usuário não
  pertencem a esta etapa.
- Quando a desativação administrativa for implementada, deve revogar todas as sessões
  do usuário para impedir que uma reativação restaure sessões antigas.
- Adicionar limpeza periódica de sessões expiradas quando o volume justificar;
  hoje elas são rejeitadas por expiração e removidas no próximo login do usuário.
- Há um aviso interno do Starlette sobre anyio.abc.BlockingPortal, já existente.
- A interface foi validada por lint, tipos e build; não há suíte de navegador ainda.

## Referências

- [FastAPI: password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Starlette: cookies](https://starlette.dev/responses/)
- [SQLAlchemy: transações em testes](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [Inter e licença](https://github.com/google/fonts/tree/main/ofl/inter)
