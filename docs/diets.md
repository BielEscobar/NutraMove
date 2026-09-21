# Dietas — Dia 6

Implementado em 10 de setembro de 2026. Sem novas dependências, Workout ou integração de IA.

## Modelos e relações

Student 1:N Diet; Professional 1:N Diet; Diet 1:N DietVersion; DietVersion 1:N Meal;
Meal 1:N Food; Food 1:N FoodSubstitution. Todos possuem UUID e chaves estrangeiras.
Diet identifica o plano e mantém seu nome inicial. Cada versão guarda seu próprio nome,
objetivo, datas, orientações e árvore de refeições: editar uma nova versão não altera o histórico.
DietVersion registra autor, aprovação, timestamps, número sequencial e edit_revision.
Quantidade usa Decimal, positiva e finita; unidade é texto livre. Não há cálculo nutricional.
Substituição permite quantidade/unidade opcionais, mas exige ambas juntas quando informadas.
Limites: 30 refeições, 50 alimentos por refeição, 20 substituições por alimento.
As posições são derivadas da ordem dos arrays pelo backend.

## Versionamento e publicação

DRAFT e PENDING_REVIEW são editáveis. APPROVED e ARCHIVED têm conteúdo imutável pela API.
Criação manual e duplicação produzem DRAFT/MANUAL; a duplicação copia também as datas,
mas gera novos IDs e não copia aprovação. Revise as datas antes de publicar.
source aceita MANUAL e AI_GENERATED. PENDING_REVIEW e AI_GENERATED estão preparados
no modelo para uma etapa futura; não há endpoint público que permita defini-los.

PATCH substitui todo o conteúdo do rascunho e exige expected_revision. A revisão evita
sobrescrever alterações de outra aba; conflitos retornam 409. Falhas desfazem toda a operação.
Aprovação também exige expected_revision, aluno ACTIVE, ao menos uma refeição e um
alimento por refeição. Registra o usuário autenticado e a data UTC. Na mesma transação,
arquiva todas as versões aprovadas anteriores daquele aluno, inclusive de outros planos.
Há uma dieta publicada vigente por aluno. Datas são informativas, sem publicação agendada.

O serviço bloqueia Student/User e Diet em ordem consistente para serializar alterações.
UNIQUE(diet_id, version_number) protege a numeração, e índice parcial impede duas versões
APPROVED do mesmo Diet. A exclusividade entre planos do aluno é garantida pelo serviço
sob bloqueio do aluno; gravações manuais no banco não substituem essas regras.
Não existe exclusão física, edição do histórico nem arquivamento manual via API.

## Autorização e visibilidade

PROFESSIONAL administra somente dietas dos alunos de sua carteira; o vínculo é obtido
do User autenticado. Consultas e mutações cruzadas retornam 404. MASTER tem somente
leitura no módulo de dietas. STUDENT consulta exclusivamente a própria publicação.
IDs da URL identificam o recurso, mas nunca concedem acesso. Campos extras de controle
são rejeitados. Operações mutáveis reutilizam a proteção Origin e sessão existentes.

GET /student/diet retorna {"diet": null} quando não há publicação ou o aluno não está ACTIVE.
Não retorna rascunhos, versões em revisão, histórico, source ou IDs internos de autoria.
Orientações e observações dos alimentos são visíveis ao aluno: não são notas privadas.

## Endpoints

| Perfil | Método | Rota |
| --- | --- | --- |
| PROFESSIONAL | GET, POST | /professional/students/{student_id}/diets |
| PROFESSIONAL | GET | /professional/diets/{diet_id} |
| PROFESSIONAL | GET, POST | /professional/diets/{diet_id}/versions |
| PROFESSIONAL | GET, PATCH | /professional/diet-versions/{version_id} |
| PROFESSIONAL | POST | /professional/diet-versions/{version_id}/duplicate |
| PROFESSIONAL | POST | /professional/diet-versions/{version_id}/approve |
| MASTER | GET | /master/students/{student_id}/diets |
| MASTER | GET | /master/diets/{diet_id} |
| MASTER | GET | /master/diets/{diet_id}/versions |
| MASTER | GET | /master/diet-versions/{version_id} |
| STUDENT | GET | /student/diet |

VersionContent valida a árvore completa; VersionUpdate acrescenta expected_revision;
ApprovalInput recebe apenas essa revisão. Schemas de resposta separam leitura administrativa
e do aluno. Repositories aplicam escopo e carregamento das relações; services controlam
transações, versão, edição, duplicação e publicação; api contém rotas e dependências de perfil.

## Interface

Professional: Meus alunos → detalhe → Dieta e versões → Novo rascunho. O editor organiza
refeições, alimentos e substituições, permite reordenar/remover, valida campos e alerta
sobre alterações não salvas. Salvar abre uma confirmação com acesso à revisão; publicar
exige confirmação separada. Histórico apresenta status, origem e versões anteriores.
MASTER usa a mesma leitura, sem botões de alteração. Student acessa Minha dieta na
navegação e no início, com refeições e substituições em cards responsivos. Sem publicação:
“Seu plano alimentar ainda não foi publicado.” Não há dados fictícios permanentes.

O editor usa chaves UUID locais estáveis, excluídas do payload. O leitor usa posições
somente no snapshot de leitura e remonta quando muda a versão/revisão; a exceção localizada
do Biome está justificada no arquivo. Não foi instalada biblioteca de formulários ou estado.

## Arquivos

Criados no backend: app/models/diet.py, app/schemas/diet.py, app/repositories/diets.py,
app/services/diets.py, app/api/diets.py, tests/test_diets.py e
alembic/versions/20260910_04_diet_versions.py. Alterados app/models/__init__.py e app/main.py
para registrar modelos e rotas. Migration 04 depende da 03 e cria cinco tabelas; revisões
anteriores foram preservadas.

Criados no frontend: src/lib/diets.ts; components/diets/{diet-editor,diet-reader,diet-list,
diet-history,version-detail,version-editor}.tsx; páginas sob professional/students/[id]/diets,
professional/diets/[id], professional/diet-versions/[id], equivalentes de leitura MASTER
e student/diet. Alterados components/students/student-detail.tsx, components/app-shell.tsx
e app/student/page.tsx para os acessos. README, architecture, validation e relatório de
contexto foram atualizados. Alterações anteriores do comando create_demo_users foram preservadas.

## Validação e limites

217 testes passaram, incluindo 32 de dieta: ownership, permissões, validação, estados,
atomicidade, histórico, visibilidade Student, revisão obsoleta e duplicações concorrentes
com PostgreSQL real. As fixtures validam upgrade/downgrade/check em schemas isolados.
Ruff check/format, mypy (61 arquivos), pip check, Biome (65 arquivos), TypeScript e build
Next.js aprovados. Permanece o DeprecationWarning interno Starlette/AnyIO já conhecido.

Chrome headless com API real e schema temporário: criação completa, salvar, aprovar,
duplicar, editar, republicar, arquivar histórico, Student ler publicação e MASTER somente
ler passaram. Editor e leitor testados em 1366, 1024, 768 e 375 px sem overflow horizontal
nem exceções JavaScript não tratadas. Capturas representativas foram inspecionadas.
Não há suíte E2E persistente instalada.

A estrutura relacional, source e PENDING_REVIEW permitem inserir futuramente sugestões
estruturadas da NutraMove AI e submetê-las à revisão profissional. Não há geração, SDK,
chave, envio de dados pessoais, publicação automática ou equivalência nutricional.
Listas de dietas/versões ainda não têm paginação; avaliar conforme volume real.
Continuam os débitos anteriores de proteção contra abuso, operação e privacidade.

## Exclusão de versões não publicadas

Professional da carteira atual pode excluir DRAFT/PENDING_REVIEW no detalhe da versão após confirmação. APPROVED/ARCHIVED retornam 409. A exclusão remove refeições, alimentos e substituições; se não houver mais versões, remove também o plano pai. O outro tipo de plano do Student não é afetado.
