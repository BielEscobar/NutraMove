# Student, onboarding e isolamento — Dia 4

Implementado em 10 de setembro de 2026. Não inclui transferência de profissional,
Diet, Workout, IA, notificações, reavaliação ou dashboard completo.

## Modelo e relações

Student tem UUID próprio e user_id obrigatório, único, com FK RESTRICT para User.
Nome, e-mail, senha, role e is_active continuam exclusivamente em User.
Professional tem relação 1:N com Student: professional_id é nullable, indexado,
com FK RESTRICT. Uma futura transferência poderá atualizar esse vínculo, mas
nenhuma rota de transferência ou atribuição posterior foi criada nesta etapa.

| Campo Student | Tipo / unidade |
| --- | --- |
| birth_date | Date, anterior ao dia atual |
| phone | Texto opcional, até 40 caracteres |
| weight / height | Float finito e positivo, kg / cm |
| goal | WEIGHT_LOSS, MUSCLE_GAIN, MAINTENANCE, FITNESS, BODY_RECOMPOSITION, OTHER |
| goal_detail | Até 500 caracteres; obrigatório somente para OTHER |
| activity_level | LOW, MODERATE, HIGH; autodeclarado |
| training_experience | NONE, BEGINNER, INTERMEDIATE, ADVANCED |
| training_frequency | Inteiro de 0 a 7 dias por semana |
| preferred_training_time | Texto opcional até 120 caracteres |
| work_routine / meal_schedule | Textos opcionais até 1000 caracteres |
| approximate_water_intake | Float finito não negativo, litros/dia, opcional |
| food_preferences / food_restrictions | Textos opcionais até 1000 caracteres |
| notes | Texto opcional até 2000 caracteres |
| water_goal | Float finito não negativo, litros/dia, definido na gestão |
| status | Enum descrito abaixo |
| created_at / updated_at | Timestamps com timezone |

Não há limites clínicos, cálculo de metas, diagnóstico ou avaliação médica.
Limites de texto são limites de armazenamento. Sexo foi omitido por não haver
uso funcional nesta etapa; telefone é opcional para contato no acompanhamento.
Não há JSON genérico com todo o cadastro.

## Cadastro e profissional

POST /students/register é público, exige Origin confiável e rejeita campos extras.
Cria User + Student em uma única transação, com role STUDENT e status
PENDING_APPROVAL fixados no servidor. A senha (12–128 caracteres) exige confirmação;
somente o hash Argon2 é persistido. E-mail é normalizado e sua duplicidade gera 409.
Resposta de cadastro contém somente status, sem sessão automática ou dados pessoais.

O aluno pode receber o link /register?professional_id=UUID, disponível no detalhe
do profissional na área MASTER, ou informar o código fornecido pelo responsável.
O backend valida Professional existente, sua role e User ativo. Não há diretório
público de profissionais. O código é apenas solicitação de vínculo inicial:
não é segredo, convite de uso único ou prova de identidade, e nunca concede acesso
a outros cadastros. O profissional confirma o acompanhamento pela aprovação.

Sem código, professional_id fica null. Apenas MASTER pode administrar esse aluno;
profissionais nunca veem alunos sem vínculo. Atribuição posterior e transferência
permanecem para outra etapa explicitamente autorizada.

## Estados e acesso

Student.status descreve o acompanhamento; User.is_active controla autenticação.

| Estado | User.is_active no fluxo implementado | Ações permitidas |
| --- | --- | --- |
| PENDING_APPROVAL | true | approve → ACTIVE; reject → REJECTED |
| ACTIVE | true | deactivate → INACTIVE |
| INACTIVE | false | activate → ACTIVE |
| REJECTED | true | Sem transição nesta etapa |

Uma transição incompatível retorna 409, inclusive repetição de ação já concluída.
Rejeitados podem entrar para ver a situação e seus próprios dados.
Desativados não entram; a página INACTIVE é defensiva, pois a API normalmente
rejeita a sessão antes disso. Aprovação não cria planos nem exige profissional
atribuído: MASTER pode analisar os cadastros sem vínculo.

Desativação preserva registros, altera User.is_active e revoga todas as sessões
na mesma transação. Reativar exige novo login. O bloqueio de User usa o mesmo
mecanismo do login existente para serializar criação e revogação de sessões.
Não há endpoint de exclusão. Desativar Professional não altera automaticamente
os cadastros nem o acesso dos seus alunos; MASTER mantém acesso administrativo.

## Endpoints

| Método | Caminho | Acesso |
| --- | --- | --- |
| POST | /students/register | Público, Origin confiável |
| GET | /students/me | STUDENT, identificado pela sessão |
| GET | /master/students | MASTER |
| GET | /master/students/{id} | MASTER |
| PATCH | /master/students/{id} | MASTER |
| POST | /master/students/{id}/approve | MASTER |
| POST | /master/students/{id}/reject | MASTER |
| POST | /master/students/{id}/activate | MASTER |
| POST | /master/students/{id}/deactivate | MASTER |
| GET | /professional/students | PROFESSIONAL |
| GET | /professional/students/{id} | PROFESSIONAL responsável |
| PATCH | /professional/students/{id} | PROFESSIONAL responsável |
| POST | /professional/students/{id}/approve | PROFESSIONAL responsável |
| POST | /professional/students/{id}/reject | PROFESSIONAL responsável |
| POST | /professional/students/{id}/activate | PROFESSIONAL responsável |
| POST | /professional/students/{id}/deactivate | PROFESSIONAL responsável |

Busca q por nome/e-mail (máximo 120 caracteres), status opcional, page >= 1 e
page_size padrão 20, máximo 100. Ordenação por nome e UUID; % e _ são literais.
MASTER também filtra por professional_id ou unassigned=true.
Query fields extras são rejeitados na listagem. Se MASTER combinar vínculo e
unassigned, aplica-se a interseção dos filtros (normalmente vazia).

PATCH edita somente dados estruturados de acompanhamento e water_goal.
Não altera nome, e-mail, senha, role, user_id, professional_id, status ou is_active.
Valida o perfil completo após combinar a alteração parcial; null não apaga campos
obrigatórios. STUDENT possui somente consulta própria nesta etapa.

## Ownership e IDOR/BOLA

A identidade vem do cookie e do User validado no banco. Para PROFESSIONAL, o
repositório busca Professional pelo User.id autenticado e adiciona
Student.professional_id == Professional.id à consulta. Essa mesma consulta é usada
na listagem, busca, detalhe, edição e em todas as transições.

Recurso inexistente ou de outra carteira retorna 404 de forma uniforme.
Não autenticado recebe 401; role incompatível ou PROFESSIONAL sem perfil recebe 403.
Parâmetros de URL, corpo ou query não substituem o escopo da sessão.
GET /students/me filtra por User.id autenticado, sem precisar de student_id.
Identificadores extras na query de /me não mudam essa identidade.

## Schemas, repositories e services

- StudentProfile: dados estruturados e validação conjunta do objetivo.
- StudentCreate: conta, confirmação de senha e vínculo inicial.
- StudentUpdate: campos editáveis, extras proibidos e patch não vazio.
- StudentBrief / StudentList: listagem mínima; sem medidas, nascimento ou notas.
- StudentResponse: detalhe autorizado, sem hash, senha, token ou user_id.
- StudentRegistrationResponse: somente status.
- StudentFilters / MasterStudentFilters: busca e filtros tipados.
- repositories/students.py: consultas SQLAlchemy com escopo aplicado antes da busca.
- services/students.py: criação atômica, atualização validada e transições explícitas.
- api/students.py: routers separados por papel, reutilizando require_roles,
  CurrentUser e a proteção de origem já existente.

## Frontend

- /register: Conta, Dados pessoais, Objetivos, Rotina, Alimentação e Revisão.
  Progresso, validação, campos obrigatórios, erro, loading, sucesso e trava de envio.
  Senha e dados ficam somente na memória da página; não há localStorage.
- /professional/students: Meus alunos, busca, filtro de status e paginação simples.
- /professional/students/{id}: detalhe, edição e ações confirmadas.
- /master/students: visão de todos, filtros de status, profissional e sem vínculo.
- /master/students/{id}: detalhe e gestão administrativa.
- /student: situação real do cadastro e dados próprios, sem planos fictícios.
- Login redireciona cada papel para sua área; /account mantém logout e links.
- O hook de carregamento existente foi extraído para useApiResource; o nome
  useMasterResource permanece como alias para preservar as telas anteriores.
- Os guardas de layout ajudam na navegação. A segurança permanece na API.

## Migration

20260910_03_students.py depende de 20260910_02. Cria students, FKs, UNIQUE de
user_id, índice de professional_id, enums como constraints e CHECKs numéricos e
de goal_detail. Nenhuma migration anterior foi alterada.
Datas futuras são rejeitadas por Pydantic; não há CHECK com data corrente mutável.

## Privacidade e alterações na fundação

Respostas de validação não repetem valores enviados. As listagens expõem apenas
nome, e-mail, objetivo, status e responsável. Campos detalhados exigem autorização.
Nenhum fluxo registra o corpo do cadastro.

SafeErrorMiddleware captura falhas antes que o servidor registre a exceção completa.
O log mantém tipo da exceção e localizações de stack (arquivo, linha, função),
sem mensagem/valores SQL ou variáveis locais. hide_parameters=True adiciona
proteção na engine. Docker usa --no-access-log, pois URLs de busca podem conter
dados pessoais; o comando de desenvolvimento no README também foi atualizado.
O proxy de produção deverá seguir uma política equivalente.

Não foi adicionada dependência. Não há SDK, chamada, prompt ou entidade de IA.
No futuro, a integração deverá selecionar campos explicitamente e prever revisão
profissional; o modelo atual não envia dados a serviços externos.

## Validação e débitos

166 testes PostgreSQL passaram, sem pulos. Cobertura inclui cadastro, atomicidade,
role/status, duplicidade, validações, aprovação/rejeição/ativação/desativação,
carteiras A/B, busca, filtros MASTER, IDOR/BOLA em todos os métodos, /me,
privacidade, CSRF, constraints e revogação de sessão. As fixtures aplicam migrations
em schemas aleatórios e verificam upgrade, downgrade e Alembic check.

Ruff check, Ruff format --check, mypy strict (49 arquivos), pip check, Biome
(42 arquivos), TypeScript e build Next.js passaram. Build Docker passou.
Permanece o DeprecationWarning interno Starlette/AnyIO já conhecido.

Débitos: limitação de tentativas/abuso no cadastro público e login, verificação de
e-mail, convite com validade caso necessário, recuperação de senha, processo de
atribuição/transferência, reconsideração de rejeitados, política de privacidade e
retenção, processo adequado para menores de idade, observabilidade e deploy.
Nenhuma regra jurídica ou médica foi presumida como conformidade implementada.


Validação no ambiente local: migration 20260910_03 aplicada; Alembic current em
head e check sem divergências, contêineres saudáveis, /health 200 e /students/me
anônimo 401. Verificação Chrome/CDP com schema isolado passou para onboarding mobile,
consulta pendente, aprovação/edição/desativação/reativação, aluno ativo e lista MASTER.
Capturas mobile/desktop inspecionadas; nenhuma exceção JavaScript não tratada.
Foi uma verificação pontual, sem dependência ou suíte E2E adicionada ao projeto.
