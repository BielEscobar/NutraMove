# Arquitetura do NUTRAMOVE

Frontend e backend são aplicações independentes no mesmo repositório.
A fundação foi preservada; a autenticação está descrita em
[authentication.md](authentication.md).

| Pasta | Finalidade |
| --- | --- |
| frontend/src/app | Rotas Next.js: login, conta, MASTER, profissional, aluno e onboarding. |
| frontend/src/components/ui | Componentes shadcn/ui. |
| frontend/src/lib | Cliente HTTP tipado e utilitários. |
| backend/app/api | Rotas HTTP e dependências de identidade e autorização. |
| backend/app/core | Configuração, hash de senhas e tratamento de erros. |
| backend/app/db | Base e sessões SQLAlchemy 2.0 síncronas. |
| backend/app/models | User, UserRole, AuthSession, Professional e Student. |
| backend/app/schemas | Contratos Pydantic de entrada e resposta. |
| backend/app/services | Autenticação e transações de gestão de profissionais e alunos. |
| backend/app/repositories | Consultas de usuários, sessões, profissionais e alunos com ownership. |
| backend/app/cli | Comando interativo de criação de MASTER. |
| backend/app/utils | Reservada para utilitários necessários no futuro. |
| backend/tests | Testes da fundação, autenticação, profissionais e isolamento de alunos. |
| backend/alembic | Migrations incrementais de usuários, sessões, profissionais e alunos. |
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

## Módulos implementados

MASTER administra Professional e todos os Students. Professional consulta e altera
somente Students vinculados ao Professional.id derivado do User autenticado.
Student consulta os próprios dados em /students/me. Repositórios aplicam esse
escopo também nas mutações; acesso cruzado retorna 404.

A relação User–Student é 1:1; Professional–Student é 1:N, com vínculo opcional.
Os serviços controlam criação atômica e transições de status, sem repositório genérico.
A migration atual é 20260911_07; revisões anteriores foram preservadas.

Frontend usa componentes de onboarding e gestão em components/students e um hook
compartilhado useApiResource. Os contratos de listagem e detalhe são separados.
SafeErrorMiddleware e logs sem valores pessoais protegem os dados do cadastro.

Consulte [profissionais](professionals.md), [Student](students.md) e
[arquivos do Dia 4](student-files.md). IA não foi implementada. Evolution foi adicionada no Dia 8. Dietas estão descritas abaixo.


## Dashboards — Dia 5

GET /master/dashboard e /professional/dashboard usam agregações SQL com o mesmo
escopo de ownership do módulo Student. GET /student/dashboard retorna um schema
mínimo do aluno autenticado. A revisão Alembic continua 20260910_03.

AppShell compartilha os layouts e a navegação por perfil. MetricCard, EmptyState e
ManagementDashboard evitam duplicação das telas; o cliente HTTP e o hook existentes
foram reutilizados. /student/profile preserva o detalhe do cadastro anterior.
Veja [dashboards.md](dashboards.md) para as decisões e o inventário de arquivos.

## Dietas — Dia 6

Student e Professional possuem Diet; Diet possui DietVersion; cada versão possui Meal,
Food e FoodSubstitution em árvore relacional. Nome e conteúdo são snapshots por versão.
Repositories aplicam ownership; services controlam bloqueios, transações e publicação.
O frontend reutiliza AppShell e useApiResource. Veja [dietas](diets.md) para contratos,
revisão concorrente, arquivos e limites. Migration 20260910_04 adiciona cinco tabelas.

## Treinos — Dia 7

Workout → WorkoutVersion → WorkoutDay → WorkoutExercise. Metadata e prescrição são
snapshots por versão, com o mesmo fluxo de autorização, bloqueio, revisão e publicação
de Diet. Repetições, carga e duração são textuais; séries e descanso são estruturados.
Sem abstração genérica de planos ou dependências novas. Consulte [workouts.md](workouts.md).
A migration 20260910_05 adiciona quatro tabelas; as anteriores permanecem intactas.

## Evolução — Dia 8

Student/Professional → Assessment → Measurement. Avaliação é o evento histórico, sem
WeightRecord redundante. Services sincronizam o peso mais recente do histórico com Student
na mesma transação e sob bloqueio. O repository aplica ownership e filtros temporais SQL.
IMC é calculado com peso e altura da avaliação, sem diagnóstico ou persistência redundante.
Recharts 3.10.1 foi adicionado ao frontend para séries responsivas com tooltip e alternativa
textual. Veja [evolution.md](evolution.md) para correções, limitações e arquivos. Migration
20260911_06 preserva as anteriores e adiciona duas tabelas.


## Hidratação e reavaliações — Dia 9

Student → WaterRecord registra consumo em ml. Meta existente em Student continua
em litros. core/time.py centraliza limites de datas; BUSINESS_TIMEZONE é validado em
Settings. Agregações usam SQL; dashboard usa resumo sem registros.

Student → ReevaluationRequest preserva destinatário original, categoria, motivo,
resposta, estado e responsáveis internos. Acesso de Professional deriva da carteira
atual. Uma solicitação aberta por aluno é protegida por locks e índice parcial.
MASTER consulta; Student envia/cancela pendente; Professional atende a carteira.

Rotas/schemas/repositories/services seguem as camadas existentes. Components hydration
e reevaluations reutilizam AppShell, useApiResource, cliente HTTP e Recharts.
Migration 20260911_07 cria as duas tabelas sem modificar revisões anteriores.
Veja [hydration.md](hydration.md), [reevaluations.md](reevaluations.md) e
[dia9-relatorio.md](dia9-relatorio.md). Não há notificações, AI ou novas dependências.

## Informativos e notificações — Dia 10

Information pertence ao Professional e pode ser geral ou individual para Student próprio. O estado DRAFT/PUBLISHED/ARCHIVED separa edição e leitura do aluno. Notification pertence ao User, com texto curto, evento controlado, recurso tipado e read_at. Services emitem eventos na mesma transação da mutação; publicação geral usa INSERT SELECT para Students ACTIVE. Repositories aplicam ownership e paginação. AppShell compartilha o sino; telas por perfil compartilham componentes de informativos. Migration 20260912_08 adiciona as tabelas. Veja [informations.md](informations.md) e [notifications.md](notifications.md).

## Transferência e AuditLog — Dia 11

Student.professional_id representa a carteira atual. Diet, Workout, Assessment e Reevaluation preservam professional_id histórico. Repositories de planos e avaliações permitem leitura do histórico pela carteira atual, enquanto mutações exigem autoria do Professional atual. Transferência bloqueia a linha Student, compara expected_professional_id e grava AuditLog no mesmo commit. IN_REVIEW impede transferência; PENDING passa à carteira nova. Information continua associada ao Professional original e Notification ao User. A migration 20260913_09 adiciona apenas audit_logs. Veja [student-transfers.md](student-transfers.md) e [audit-log.md](audit-log.md).

## NutraMove AI — Dia 12

A fronteira pp/ai/provider.py chama a Responses API; generation.py monta contexto mínimo e cria Diet/Workout novos com versões AI_GENERATED/PENDING_REVIEW. O editor, a aprovação e Notification existentes continuam responsáveis pela publicação. Sem nova tabela ou migration. Veja [nutramove-ai.md](nutramove-ai.md).

## Hardening — Dia 13

`core/rate_limit.py` usa `rate_limit_windows` no PostgreSQL, HMAC de identidade/endereço e UPSERT atômico para login, cadastro e IA. `SecurityHeadersMiddleware` adiciona headers e no-store às respostas da API; Next config adiciona headers de proteção ao frontend. `Settings` exige CORS HTTPS não loopback e `RATE_LIMIT_SECRET` explícito em produção; docs API ficam desabilitadas por padrão nesse ambiente. Migration `20260913_10` depende de `20260913_09`. Veja [security.md](security.md) e [privacy-lgpd.md](privacy-lgpd.md).