# NUTRAMOVE — Contexto atual para próximos prompts

Atualizado em 11 de setembro de 2026, após o Dia 9.

## Estado real

Implementados: fundação, autenticação por sessão opaca, MASTER + gestão de
profissionais, Student + onboarding + isolamento e dashboards por perfil.
Dietas com versões e publicação foram implementadas no Dia 6. Workout foi implementado no Dia 7. Evolução física foi implementada no Dia 8. Não existem IA, transferência de alunos ou notificações.
Hidratação e solicitações de reavaliação foram implementadas no Dia 9.
O trabalho encerrou no Dia 9; próximas funcionalidades exigem autorização.

Repositório informado: BielEscobar/NutraMove. Branch local: develop.
main é reservada para produção. O Dia 8 começou com alteração local apenas em docs/workouts.md, preservada. Confirme Git e arquivos antes de qualquer edição.

## Estado técnico atual — Dia 9

HEAD local aplicado: **20260911_07**, dependente de 20260911_06. Alembic check sem
divergências. 344 testes passaram; Ruff/format/mypy (89 arquivos), pip check,
Biome, TypeScript, Next build, Compose e Docker aprovados. Resultados abaixo relativos
a dias anteriores são históricos, não representam o HEAD atual.

- WaterRecord registra inteiro amount_ml, consumed_at aware, created_at e Student.
  Student.water_goal continua em litros. BUSINESS_TIMEZONE padrão America/Sao_Paulo.
  Resumo/1/7/30 dias usam SUM e data local SQL; sem DELETE ou meta automática.
- ReevaluationRequest tem DIET/WORKOUT/EVOLUTION/DIFFICULTY/OTHER e estados
  PENDING/IN_REVIEW/COMPLETED/CANCELLED. Criação só Student ACTIVE com profissional ativo;
  uma solicitação aberta total por aluno, protegida por lock e índice parcial.
- Professional da carteira atual inicia análise, conclui com resposta ou cancela.
  Student cancela somente pendente; MASTER somente consulta. Destinatário original
  é preservado, mas não concede acesso isoladamente. Transferência segue pendente.
- Menus Hidratação/Solicitar reavaliação no Student, Reavaliações no staff;
  card de água real e contagens PENDING/IN_REVIEW no dashboard profissional.
- Chrome/API real validou fluxo completo, duplicidade/cancelamento, meta, erro/retry,
  leitura MASTER e isolamento; 1366/1024/768/375 px sem overflow nem exceções JS.
- Nenhuma dependência nova no Dia 9. Sem commit. Alterações locais do Dia 8 preservadas.

Leia [hidratação](hydration.md), [reavaliações](reevaluations.md) e
[relatório completo](dia9-relatorio.md) antes do próximo prompt. Não implementar
notificações, AI, transferência ou auditoria geral sem novo escopo autorizado.

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

## Histórico de migrations e validação do Dia 5

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
preparam um contrato futuro sem integração real. Este trecho registra o encerramento do Dia 6; Workout foi autorizado e implementado no Dia 7, descrito abaixo.
Migration 04 preserva as anteriores. Resultado registrado no Dia 6: 217 testes, Ruff, mypy (61 arquivos),
pip check, Biome (65 arquivos), tipos e build aprovados. Chrome validou o fluxo completo
e quatro larguras sem overflow. Não há suíte E2E persistente. Aviso Starlette/AnyIO permanece.
O comando local create_demo_users e alterações anteriores no README foram preservados.

Banco local atualizado para 20260910_04 (head), Alembic check sem divergências e
contêineres saudáveis. Configuração Compose e imagem Docker validadas.

## Atualização do Dia 7 — Workout

Consulte [workouts.md](workouts.md) para modelos, endpoints, inventário e decisões.
O checkout inicial estava limpo em develop. HEAD real inicial: 20260910_04; nova revisão:
20260910_05, com workouts, workout_versions, workout_days e workout_exercises.

Professional cria/edita/duplica/publica para aluno próprio; MASTER somente lê; Student
ACTIVE consulta exclusivamente seu treino APPROVED em /student/workout (ou workout:null).
Os filhos não têm endpoints próprios ou IDs aceitos na edição composta. Datas, nome,
objetivo e prescrição são copiados por versão. Séries 1–100, descanso 0–86400 segundos,
frequência 1–7; repetições/carga/duração textuais. Divisões livres, sem limite A/B/C.

Publicação arquiva a anterior do aluno na mesma transação, com autor/data; duplicação
produz DRAFT/MANUAL com novos IDs e sem aprovação. expected_revision e bloqueios evitam
sobrescrita obsoleta e numeração concorrente. Diet não foi refatorado nem teve regras alteradas.

Frontend inclui editor, histórico, leitor móvel e Meu treino na navegação. Dashboard
Student consulta disponibilidade real e oferece Ver treino; Minha dieta foi preservada.
Nenhuma dependência nova. Resultado: 260 testes, incluindo 43 de treino; Ruff, mypy
(68 arquivos), pip check, Biome (83 arquivos), TypeScript e build Next.js aprovados.
Permanece o aviso interno Starlette/AnyIO. Veja validation.md para validação final.

Não existem IA real, biblioteca global, mídia de exercício, cronômetro, execução do treino,
registro de carga, progressão ou Evolution. Paginação e suíte E2E persistente seguem
pendentes. source/status permitem futura sugestão revisada, sem autorizar geração ou Dia 8.
Validação final do Dia 7: migration local 20260910_05 (head), Alembic check sem divergências,
backend e PostgreSQL saudáveis. Chrome headless com API real validou login, abertura do
aluno, criação de divisão/exercício, salvar/publicar, leitura Student, duplicação/edição,
histórico intacto antes de republicar e entrega da versão 2 ao aluno. MASTER somente leitura.
Editor e leitor foram testados em 1366, 1024, 768 e 375 px sem overflow horizontal ou
exceções JavaScript não tratadas. Capturas representativas dos quatro tamanhos foram
inspecionadas visualmente, incluindo instruções abertas em 375 px. Não há suíte E2E
persistente; os testes usaram schema e contas temporários, removidos ao terminar.

## Atualização do Dia 8 — Avaliações e evolução

Veja [evolution.md](evolution.md) para contratos, arquivos e decisões completos.
Assessment é o evento principal (data civil, peso/altura opcionais, notas, autoria e última
correção, timestamps, edit_revision), com Measurement tipada e lateralidade opcional.
Sem WeightRecord redundante, sem cópia automática do onboarding e sem avaliações fictícias.

Peso atual deriva da avaliação mais recente COM peso: assessment_date, created_at, UUID
(descendentes). Criação/correção e Student.weight são atômicos, sob bloqueio. Correção antiga
e lançamento retroativo não vencem avaliação mais recente. Perfil não pode alterar weight
quando já há peso histórico; a correção deve ocorrer na avaliação. Altura do perfil não muda.
Peso existente pode ser corrigido, mas não removido. PATCH recebe conteúdo completo e
expected_revision; preserva data/vínculo, atualiza autoria/timestamp/revisão. Não guarda
valores anteriores da correção, apenas avaliações distintas e metadados da última alteração.

IMC calculado no backend só com peso e altura do mesmo snapshot, sem diagnóstico. Falta
de altura retorna null. Não usa altura atual do perfil para recalcular o passado.
Professional opera apenas própria carteira (404 uniforme); Student consulta somente próprios
registros; MASTER lê. Avaliações não possuem aprovação/publicação como Diet e Workout.

Endpoints /professional/students/{id}/assessments e /evolution, /professional/assessments/{id};
MASTER equivalentes GET; Student /student/evolution, /student/assessments e /{id}.
Listagem paginada 20/máximo100; gráfico filtra no SQL 7d/30d/90d/6m/1y/all, resumo current
global. Histórico completo da tela é independente do período. Sem polling ou cache adicional.

Frontend tem Nova avaliação, correção, medidas, gráfico de uma série por vez, tooltip,
alternativa textual, histórico, detalhe, Minha evolução e resumo real no dashboard.
Recharts 3.10.1 instalado e lockfile atualizado; demais módulos preservados.
Migration nova 20260911_06, dependente do HEAD real 20260910_05, aplicada localmente.
293 testes passaram (33 novos), Ruff/mypy (75 arquivos)/pip check aprovados. Sem divergências
Alembic; Compose e imagem Docker aprovados. Aviso interno Starlette/AnyIO permanece.

Pendentes: auditoria de valores corrigidos, correção de datas, retenção/privacidade, limites
do gráfico all e suíte E2E persistente. Não há IA, hidratação, workflow de reavaliação,
notificações, fotos, gordura corporal, diagnóstico, alteração automática de planos ou Dia 9.

Validação final Dia 8: Biome 97 arquivos, TypeScript e build Next.js aprovados. Chrome/API
real validou duas avaliações, correção, gráficos/tooltip, perfis e quatro larguras sem overflow.
Capturas inspecionadas; dados temporários removidos. Build EPERM de .next resolvido com
limpeza somente dos artefatos gerados após encerrar o dev. Veja evolution.md e validation.md.

## Estado complementar — Dia 10

Informativos e notificações internas foram adicionados na revisão 20260912_08. Information tem audiência geral ou individual e estados DRAFT/PUBLISHED/ARCHIVED. Notification pertence a User e eventos são transacionais. Acesso a informativos de carteira anterior e links de notificações após transferência exigem política explícita no Dia 11. Não há IA, push, e-mail, cron ou transferência implementados neste Dia.

## Estado complementar — Dia 11

Transferência MASTER de Student e AuditLog foram adicionados na revisão 20260913_09. O vínculo atual muda; autoria de Diet/Workout/Assessment/Reevaluation não muda. Novo Professional lê histórico mas não edita registros do anterior. Plano APPROVED atual permanece para Student. IN_REVIEW bloqueia transferência; PENDING passa à operação da carteira nova. Information antiga deixa de aparecer ao Student; Notification permanece no User. Dia 12/AI não foi implementado.
