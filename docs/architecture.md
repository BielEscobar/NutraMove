# Arquitetura do NUTRAMOVE

Frontend e backend são aplicações independentes no mesmo repositório.
A fundação foi preservada; a autenticação está descrita em
[authentication.md](authentication.md).

| Pasta | Finalidade |
| --- | --- |
| frontend/src/app | Rotas e layouts Next.js, login e página da conta. |
| frontend/src/components/ui | Componentes shadcn/ui. |
| frontend/src/lib | Cliente HTTP tipado e utilitários. |
| backend/app/api | Rotas HTTP e dependências de identidade e autorização. |
| backend/app/core | Configuração, hash de senhas e tratamento de erros. |
| backend/app/db | Base e sessões SQLAlchemy 2.0 síncronas. |
| backend/app/models | User, UserRole e AuthSession. |
| backend/app/schemas | Contratos Pydantic de entrada e resposta. |
| backend/app/services | Operações de autenticação e criação administrativa de MASTER. |
| backend/app/repositories | Consultas de usuários e sessões. |
| backend/app/cli | Comando interativo de criação de MASTER. |
| backend/app/utils | Reservada para utilitários necessários no futuro. |
| backend/tests | Testes da fundação e autenticação. |
| backend/alembic | Migration de usuários e sessões, sem alteração de revisões aplicadas. |
| infra | Compose local de backend e PostgreSQL. |
| docs | Decisões e instruções. |

## Persistência e configuração

Pydantic Settings lê backend/.env e variáveis do processo, que têm precedência.
DATABASE_URL exige PostgreSQL e o driver psycopg.
Cada requisição que precisa de banco usa uma Session; os serviços controlam commits.
Sessões são fechadas ao final e transações pendentes são desfeitas.

Alembic usa Base.metadata e os modelos importados por app/models/__init__.py.
Não há criação automática de tabelas no startup.
A fábrica create_app permite configurar a API para execução e testes.

## Autenticação e autorização

O backend armazena sessões revogáveis e consulta a role real do usuário em cada
requisição protegida. O navegador recebe somente um cookie HttpOnly para identidade.
Não há tokens em localStorage nem roles aceitas do cliente como autorização.
Senhas usam Argon2; APIs retornam schemas explícitos sem password_hash.

CORS permite cookies apenas para origens explícitas. Requisições que alteram dados
também validam Origin para proteção CSRF. Configuração de produção exige cookie
Secure e frontend HTTPS.

## Frontend

Next.js App Router, React e TypeScript. Os formulários são componentes client e
usam a API FastAPI real. A navegação não substitui autorização no backend.
Tailwind e shadcn/ui mantêm a base visual; Lucide fornece ícones.
Inter é local e distribuída com a licença OFL.
Biome verifica lint/formatação; TypeScript verifica tipos.

## Infraestrutura

O Compose é para desenvolvimento local: backend e PostgreSQL 17, portas vinculadas
a 127.0.0.1 e volume persistente. O frontend roda com npm.
O backend usa usuário sem privilégios de root no contêiner.
Migrations são executadas explicitamente, antes de usar novas rotas.

develop é a branch de desenvolvimento; main é reservada para produção.
TLS, proxy, backups e deploy na Hostinger não foram implementados.
Dependências Python diretas estão fixadas; as transitivas ainda não têm lockfile.
O frontend utiliza package-lock.json.

## Próxima etapa

Gestão de profissionais por MASTER, com entidade Professional associada ao User.
STUDENT existe apenas como role para autorização futura; não há entidade ou módulo
de alunos. Também não existe integração de IA.
