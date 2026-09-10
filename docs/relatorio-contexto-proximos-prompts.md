# NUTRAMOVE — Contexto atual para próximos prompts

Atualizado em 10 de setembro de 2026, após o Dia 6.

## Estado real

Implementados: fundação, autenticação por sessão opaca, MASTER + gestão de
profissionais, Student + onboarding + isolamento e dashboards por perfil.
Dietas com versões e publicação foram implementadas no Dia 6. Não existem Workout, IA, transferência de alunos ou notificações.
O trabalho encerrou no Dia 6; próximas funcionalidades exigem autorização.

Repositório informado: BielEscobar/NutraMove. Branch local: develop.
main é reservada para produção. As alterações locais dos Dias 3, 4 e 5 estão sem
commit e foram preservadas. Confirme Git e arquivos antes de qualquer edição.

## Regras do projeto

O responsável aprende Python e usa o projeto como portfólio. Prefira código
simples, tipado e organizado. Preserve a arquitetura existente, explique
complexidade relevante e não acrescente funcionalidades fora do pedido.
Não crie commits automaticamente. Execute testes, lint, tipos e build aplicáveis,
comunique falhas e pare ao concluir a etapa.

Backend: Python/FastAPI, SQLAlchemy 2.0 síncrono, Pydantic, Alembic e PostgreSQL.
Frontend desacoplado: Next.js/React/TypeScript, Tailwind, shadcn/ui e Lucide.
Biome verifica o frontend; pytest, Ruff e mypy strict verificam o backend.
Infra local: Docker Compose, PostgreSQL 17, backend como appuser.
Nenhuma dependência nova foi adicionada nos módulos Professional e Student.
Hostinger VPS é destino futuro, sem deploy implementado.

## Entidades reais

- User: UUID, name, email normalizado/único, password_hash Argon2, role,
  is_active, timestamps. Roles MASTER, PROFESSIONAL, STUDENT.
- AuthSession: hash SHA-256 do token opaco, user_id, criação e expiração.
- Professional: UUID, user_id obrigatório e único, specialty opcional, timestamps.
- Student: UUID, user_id obrigatório e único, professional_id opcional, dados
  estruturados de perfil, status e timestamps.

Nome, e-mail, senha, role e is_active pertencem a User. Não duplicar nas entidades.
Student não é profile_json: possui nascimento, telefone opcional, peso em kg,
altura em cm, objetivo e complemento, atividade, experiência, frequência em
dias/semana, rotina, alimentação, notas e água em litros/dia.
Veja [students.md](students.md) para todos os campos, enums e limites.

## Autenticação e segurança

Preservada a sessão opaca PostgreSQL, cookie HttpOnly/SameSite=Lax, expiração
absoluta, Secure em produção e nenhuma persistência de token no localStorage.
Rotas /auth/login, /auth/me e /auth/logout permanecem. CLI create_master é a
forma administrativa de criar MASTER; nenhuma conta padrão foi criada.

get_current_user consulta usuário ativo e sessão no banco.
require_roles usa a role real do User. Operações mutáveis validam Origin.
CORS permite GET, POST e PATCH, com credenciais e origens explícitas.
Nunca confiar em role, user_id, professional_id ou student_id para conceder acesso.

O login e as desativações bloqueiam a mesma linha User para serializar geração
e revogação de sessões. Desativações administrativas revogam todas as sessões.
Reativação exige novo login; alteração manual de dados no banco não equivale a
executar as regras dos serviços.

Erros inesperados registram tipo e localizações da stack sem valores pessoais.
SafeErrorMiddleware impede que a exceção completa seja registrada pelo servidor.
Engine usa hide_parameters=True. Docker e comando local recomendado usam
--no-access-log para evitar registrar nomes/e-mails presentes nas buscas.

## MASTER + Professional

Rotas /master/professionals: criar, listar, resumo, detalhe, PATCH, activate e
deactivate. Somente MASTER. Criação gera novo User + Professional atomicamente,
role PROFESSIONAL fixada no backend. MASTER define a senha inicial.
Edição: nome, e-mail e specialty. Sem exclusão física ou vínculo com User existente.
Área /master possui visão geral, profissionais e alunos.
Detalhe do profissional oferece código e link de cadastro de alunos.

## Student e onboarding

POST /students/register é público, exige Origin confiável, cria User + Student
atomicamente, role STUDENT e status PENDING_APPROVAL fixados no servidor.
Exige confirmação de senha. Retorna somente status; não abre sessão automaticamente.
Cadastro pode receber professional_id válido e ativo pelo link/código.
Não há lista pública de profissionais. O código não é segredo nem fonte de autorização.
Sem vínculo, somente MASTER administra o cadastro. Não há atribuição posterior
nem transferência implementadas.

Estados:
- PENDING_APPROVAL: pode entrar; aprovar → ACTIVE, rejeitar → REJECTED.
- ACTIVE: pode entrar; desativar → INACTIVE.
- INACTIVE: User.is_active=false, sessões revogadas; reativar → ACTIVE.
- REJECTED: pode entrar para consultar situação e dados; sem transição posterior.

Transições inválidas retornam 409. Aprovação não gera planos.
MASTER pode administrar sem vínculo. Desativar Professional não desativa seus alunos.

## Endpoints e ownership Student

GET /students/me consulta exclusivamente o User autenticado com role STUDENT.

MASTER usa /master/students e PROFESSIONAL usa /professional/students:
- GET coleção e /{id}.
- PATCH /{id}, somente dados do acompanhamento e water_goal.
- POST /{id}/approve, reject, activate e deactivate.

Professional.id é obtido a partir do User.id autenticado. Toda consulta de carteira
inclui esse vínculo, antes de buscar o aluno. Aluno de outra carteira ou inexistente
retorna 404 uniformemente, inclusive nas mutações. Anônimo recebe 401; role
incompatível recebe 403. STUDENT não usa rotas administrativas.

Busca por nome/e-mail; status; paginação simples padrão 20, máximo 100.
MASTER também filtra professional_id e unassigned.
Listagem não expõe nascimento, peso, restrições, notas ou outros dados detalhados.
Schemas não retornam senha, hash, token ou user_id.
Não há edição de nome/e-mail/senha do Student nesta etapa.

## Frontend

- /login: destino por role; link para cadastro.
- /account: conta, logout e acesso às áreas.
- /register: seis etapas (Conta, Dados pessoais, Objetivos, Rotina, Alimentação,
  Revisão), validação, loading, erros, sucesso e prevenção de duplo envio.
- /professional: dashboard; /professional/students: carteira e detalhe com edição/ações.
- /master/students: gestão completa e filtros.
- /student: dashboard resumido; /student/profile: dados próprios completos.
- AppShell compartilha sidebar adaptada, cabeçalho, identidade e logout dos três perfis.
- Login consulta /auth/me e direciona MASTER → /master, PROFESSIONAL → /professional,
  STUDENT → /student. Configurações futuras foram omitidas; conta existente preservada.

Dados de onboarding ficam apenas na memória da página.
useApiResource reutiliza o carregamento existente, com cancelamento e erros.
useMasterResource permanece como alias compatível.

## Migrations e validação atual

- 20260910_01: users e auth_sessions.
- 20260910_02: professionals.
- 20260910_03: students, FKs, UNIQUE, índice e constraints.

Dia 5 não alterou modelos nem migrations. No Dia 5, o banco estava na revisão 20260910_03; o Dia 6 adiciona 20260910_04.
Alembic check sem divergências; contêineres saudáveis.
As fixtures de testes verificam upgrade/downgrade/check em schemas isolados.

Resultados do Dia 5:
- pytest: 185 passaram, nenhum pulado.
- Ruff check e format --check: aprovados.
- mypy strict: 53 arquivos, sem erros.
- pip check: sem incompatibilidades.
- Biome: 48 arquivos, aprovado.
- TypeScript e build Next.js: aprovados.
- Compose config --quiet, build Docker, Alembic current/check: aprovados.
- Chrome/CDP: dashboards dos três papéis em 1366, 1024, 768 e 375 px, sem
  overflow horizontal; login, logout, navegação, proteção de páginas, erro/retry,
  aluno pendente/rejeitado e carteira vazia passaram.
- Capturas representativas dos quatro tamanhos foram inspecionadas visualmente.
- Nenhuma exceção JavaScript não tratada.

O navegador usou API real e dados sintéticos em schema temporário. Falhas de API
foram simuladas transitoriamente por bloqueio de rede no navegador, sem mocks
permanentes. Não há suíte E2E instalada. No Dia 4 também foi verificado o onboarding.
Permanece o DeprecationWarning interno Starlette/AnyIO.

## Dashboards reais — Dia 5

GET /master/dashboard agrega profissionais e alunos globais por status e sem vínculo.
GET /professional/dashboard agrega apenas a carteira da sessão e cinco cadastros
recentes. GET /student/dashboard retorna dados mínimos do próprio aluno.
Os três endpoints têm schemas próprios e require_roles. IDs enviados na query
não alteram o escopo. COUNT/FILTER são executados no banco; não há contagem de
coleções completas em Python. Consultas de recentes usam LIMIT 5, sem N+1.
Não há histórico inventado, polling, gráfico fictício ou novas dependências.

Layouts: MASTER tem Dashboard/Profissionais/Alunos; PROFESSIONAL tem
Dashboard/Meus alunos; STUDENT tem Início/Meu perfil. Conta e logout no cabeçalho.
Aluno ativo vê estados futuros de treino/dieta/evolução sem links nem dados falsos.
Confira [dashboards.md](dashboards.md) para arquivos, decisões e validação.


## Comandos

Dentro de backend/:
```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pip check
```

Dentro de frontend/:
```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Na raiz:
```powershell
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic current
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic check
```

## Débitos e decisões futuras

Rate limiting de login/cadastro, verificação de e-mail, recuperação/troca de senha,
convites caso necessários, atribuição/transferência, revisão de rejeição, política
de privacidade/retenção e processo para menores, suíte E2E persistente, lockfile
Python transitivo, HTTPS/proxy/backups/observabilidade/deploy continuam pendentes.
Não tratar cadastro público como pronto para exposição em produção.
Dados estruturados permitem futura seleção explícita para IA; nenhuma integração
de IA foi criada nem autorizada automaticamente.

## Documentação detalhada

- [students.md](students.md): modelo, estados, endpoints, isolamento e decisões.
- [student-files.md](student-files.md): arquivos criados/modificados no Dia 4.
- [professionals.md](professionals.md): módulo MASTER + Professional.
- [authentication.md](authentication.md): sessão e limites.
- [architecture.md](architecture.md): organização.
- [validation.md](validation.md): histórico de verificações.

## Atualização do Dia 6 — Diet

Consulte [diets.md](diets.md) para o contexto completo e inventário de arquivos.
Diet → DietVersion → Meal → Food → FoodSubstitution, com snapshots e revisão otimista.
Professional cria/edita/duplica/publica apenas na própria carteira; MASTER somente lê.
Student ACTIVE consulta somente a dieta aprovada atual em /student/diet. Publicação arquiva
a anterior do aluno atomicamente. DRAFT/MANUAL é o padrão; PENDING_REVIEW/AI_GENERATED
preparam um contrato futuro sem integração real. Não há Workout ou autorização para Dia 7.
Migration 04 preserva as anteriores. Resultado atual: 217 testes, Ruff, mypy (61 arquivos),
pip check, Biome (65 arquivos), tipos e build aprovados. Chrome validou o fluxo completo
e quatro larguras sem overflow. Não há suíte E2E persistente. Aviso Starlette/AnyIO permanece.
O comando local create_demo_users e alterações anteriores no README foram preservados.

Banco local atualizado para 20260910_04 (head), Alembic check sem divergências e
contêineres saudáveis. Configuração Compose e imagem Docker validadas.
