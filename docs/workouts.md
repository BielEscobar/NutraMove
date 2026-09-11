# Treinos — Dia 7

Implementado em 10 de setembro de 2026. O módulo permite prescrição manual, versões,
publicação e leitura pelo aluno. Não adiciona dependências, IA ou Evolution.

## Modelos e relações

```text
Student 1:N Workout N:1 Professional
                |
                1:N WorkoutVersion
                         |
                         1:N WorkoutDay
                                  |
                                  1:N WorkoutExercise
```

- Workout: UUID, FKs obrigatórias Student/Professional, nome inicial e timestamps.
- WorkoutVersion: UUID, FK Workout, número sequencial, edit_revision, nome, objetivo,
  status, source, autor, aprovador/data, início, próxima revisão, frequência semanal,
  orientações e timestamps. Nome e objetivo pertencem ao snapshot: futuras alterações
  não mudam versões anteriores. O nome inicial do Workout identifica o plano na lista.
- WorkoutDay: UUID, FK de versão, nome livre, descrição opcional e posição.
- WorkoutExercise: UUID, FK de divisão, nome, grupo muscular, descrição, instruções,
  séries, repetições, carga, duração, descanso, observações e posição.

Divisões e exercícios não possuem timestamps próprios: seguem o padrão dos filhos de
Diet e são substituídos atomicamente na edição do snapshot. A versão registra atualização.
FKs dos planos/autoria usam RESTRICT; filhos do snapshot usam CASCADE e delete-orphan.
Não há exclusão física exposta pela API.

## Prescrição e schemas

ExerciseInput valida o exercício; DayInput contém exercises[]; VersionContent contém
metadata e days[]. VersionUpdate acrescenta expected_revision; ApprovalInput recebe
somente essa revisão. Schemas de resposta separam leitura administrativa e Student.
Campos extras são rejeitados, inclusive IDs dos filhos, role, autoria, status e source.
A ordem dos arrays determina position no backend, sem aceitar posições arbitrárias.

| Campo | Representação e limite V1 |
| --- | --- |
| name | Texto obrigatório, 1–160 caracteres após trim |
| frequency_per_week | Inteiro opcional, 1–7 dias/semana |
| sets | Inteiro opcional, 1–100 |
| repetitions | Texto opcional, até 160: 8-12, falha, 12 por lado |
| load | Texto opcional, até 160: 20 kg, Peso corporal, RPE 8 |
| duration | Texto opcional, até 160: 30 segundos, cadência descrita |
| rest_seconds | Inteiro opcional, 0–86400; zero é descanso explicitamente nulo |
| muscle_group | Texto opcional, até 160 |
| descrição/instruções/notas do exercício | Texto opcional, até 2000 cada |
| goal / notes da versão | Até 500 / 4000 caracteres |
| days / exercises | Até 30 divisões e 100 exercícios por divisão |

Limites são de validação e capacidade, não recomendações de treinamento.
Números booleanos/fracionários são rejeitados nos campos inteiros. Não se exige séries
ou repetições para exercícios baseados em tempo. Não há cálculo de carga, equivalência,
progressão ou descanso automático. Próxima revisão não pode preceder o início.

## Workflow, histórico e concorrência

Criação manual: Workout + versão 1 DRAFT/MANUAL na mesma transação.
Nova versão em branco: próximo número no mesmo Workout, DRAFT/MANUAL.
Duplicação: copia metadata (inclusive datas), frequência, divisões e exercícios com
prescrição e ordem; gera novos UUIDs, DRAFT/MANUAL, sem aprovador/data de aprovação.
Revise as datas copiadas antes de publicar.

DRAFT e PENDING_REVIEW são editáveis. PATCH substitui o conteúdo completo da versão,
não apenas os campos presentes. expected_revision evita perda de alterações entre abas;
edição e aprovação com revisão obsoleta retornam 409. Falhas desfazem toda a árvore.
APPROVED e ARCHIVED não permitem edição: duplicar ou criar uma nova versão.

Publicação exige Student ACTIVE, ao menos uma divisão e um exercício em cada divisão.
Registra CurrentUser.id e timestamp UTC; arquiva a publicação anterior do aluno na mesma
transação, inclusive se pertencer a outro Workout. Conteúdo e autoria anteriores permanecem.
Há um treino vigente por aluno. Diet e Workout são independentes: publicar treino não
arquiva dieta. Datas são informativas, sem agendamento ou expiração automática.

Services bloqueiam Student/User e depois Workout em ordem consistente; a numeração é
calculada sob esse bloqueio e protegida por UNIQUE(workout_id, version_number).
Índice parcial único impede duas APPROVED do mesmo Workout. A exclusividade entre
Workouts do aluno depende do bloqueio e fluxo do serviço, como em Diet; gravação manual
no banco não substitui as regras. Não foi introduzida infraestrutura de locks distribuídos.

## Ownership e IDOR/BOLA

Repositories reutilizam o escopo Student existente, derivando Professional do User da
sessão. Exigem aluno da carteira e consistência com Workout.professional_id. Toda leitura
e mutação resolve o plano/versão nesse escopo; recurso alheio ou inexistente retorna 404.
Anônimo recebe 401; perfil incompatível recebe 403. Mutações validam Origin confiável.
MASTER possui somente leitura administrativa e nunca se torna autor por esse acesso.

Não há endpoints isolados para WorkoutDay/WorkoutExercise. Leitura e alteração dos filhos
passam pela versão autorizada; IDs enviados na árvore são rejeitados. Os testes cobrem
as nove rotas Professional contra outra carteira e tentativas de injetar IDs dos filhos.
Logs, sessão opaca, CORS e tratamento seguro de erros permanecem os existentes.

## Endpoints

| Perfil | Método | Rota |
| --- | --- | --- |
| PROFESSIONAL | GET, POST | /professional/students/{student_id}/workouts |
| PROFESSIONAL | GET | /professional/workouts/{workout_id} |
| PROFESSIONAL | GET, POST | /professional/workouts/{workout_id}/versions |
| PROFESSIONAL | GET, PATCH | /professional/workout-versions/{version_id} |
| PROFESSIONAL | POST | /professional/workout-versions/{version_id}/duplicate |
| PROFESSIONAL | POST | /professional/workout-versions/{version_id}/approve |
| MASTER | GET | /master/students/{student_id}/workouts |
| MASTER | GET | /master/workouts/{workout_id} |
| MASTER | GET | /master/workouts/{workout_id}/versions |
| MASTER | GET | /master/workout-versions/{version_id} |
| STUDENT | GET | /student/workout |

POST de criação/duplicação retorna 201. Edição/aprovação e consultas retornam 200.
Respostas utilizam no-store. Valores inválidos retornam 422; conflitos de revisão,
edição de histórico ou aluno sem acompanhamento ativo na publicação retornam 409.

Student deriva exclusivamente de User autenticado. Retorno tipado {"workout": null}
quando não há publicação ou o aluno não está ACTIVE. Somente APPROVED é retornada,
ordenada por approved_at e UUID descendentes para resultado determinístico. Nenhum ID
recebido por query altera a escolha do aluno. Não retorna source, autoria interna, IDs
internos dos filhos, senha ou token. Observações são visíveis ao aluno, não notas privadas.

## Frontend e dashboard

Professional: Meus alunos → aluno → Treino e versões → Criar treino. Editor com metadata,
divisões e exercícios, botões Subir/Descer, confirmação para remover, validações, estados
de envio/erro/sucesso e aviso de saída com alterações não salvas. Salvar não publica:
Revisar versão leva à confirmação separada de publicação. Histórico permite consultar,
duplicar ou iniciar uma versão em branco. Chaves locais estáveis não são enviadas à API.

Student: Meu treino na navegação abre /student/workout. Sem publicação, exibe
“Seu treino ainda não foi publicado.” A leitura usa divisões e lista de exercícios,
séries/repetições destacadas, carga e descanso visíveis, instruções expansíveis e sem
tabela horizontal. MASTER usa o mesmo leitor sem ações de edição.

Dashboard Student recebeu somente disponibilidade real e link Ver treino. Essa seção
consulta o endpoint existente de treino, sem métrica fictícia ou polling. Minha dieta
foi preservada. A informação ainda carrega o conteúdo do plano completo; avaliar um
resumo específico se o volume justificar. Não houve redesenho dos dashboards.

## Arquivos criados e modificados

Criados backend:
- app/models/workout.py: quatro entidades, enums, relações e constraints.
- app/schemas/workout.py: entradas e respostas tipadas.
- app/repositories/workouts.py: consultas com escopo e carregamento da árvore.
- app/services/workouts.py: transações, criação, edição, duplicação e publicação.
- app/api/workouts.py: rotas por perfil reutilizando dependências existentes.
- tests/test_workouts.py: 43 testes incluindo casos parametrizados.
- alembic/versions/20260910_05_workout_versions.py: quatro tabelas e índices.

Modificados backend: app/main.py registra routers; app/models/__init__.py registra modelos.

Criados frontend:
- src/lib/workouts.ts: contratos e nomes de status.
- src/components/workouts/workout-editor.tsx, workout-reader.tsx, workout-list.tsx,
  workout-history.tsx, version-detail.tsx, version-editor.tsx e workout-availability.tsx.
- src/app/professional/students/[id]/workouts/page.tsx e new/page.tsx.
- src/app/professional/workouts/[id]/page.tsx e versions/new/page.tsx.
- src/app/professional/workout-versions/[id]/page.tsx e edit/page.tsx.
- src/app/master/students/[id]/workouts/page.tsx.
- src/app/master/workouts/[id]/page.tsx e master/workout-versions/[id]/page.tsx.
- src/app/student/workout/page.tsx.

Modificados frontend: components/app-shell.tsx, components/students/student-detail.tsx
e app/student/page.tsx. Documentação: este arquivo, README, architecture, validation
e relatorio-contexto-proximos-prompts. Nenhuma dependência ou arquivo de Diet foi alterado.

## Migration e testes

HEAD inicial confirmado no código e banco: 20260910_04. Nova revisão 20260910_05 depende
dela; nenhuma migration anterior foi modificada. Cria workouts, workout_versions,
workout_days e workout_exercises, FKs, índices, UNIQUE e CHECKs. Upgrade/downgrade/check
foram executados pelas fixtures em schemas PostgreSQL descartáveis.

260 testes passaram, nenhum pulado, incluindo 43 de treino. Cobertura: criação,
source/status impostos no backend, prescrição flexível, BOLA/IDs injetados, perfis,
Origin, visibilidade Student, histórico, deep copy, reordenação, revisão obsoleta,
atomicidade de criação/edição/publicação e numeração concorrente com duas sessões reais.
Ruff check e format, mypy (68 arquivos), pip check, Biome (83 arquivos), TypeScript e
build Next.js aprovados. Permanece o DeprecationWarning interno Starlette/AnyIO.

## Coerência com Diet e preparação futura

Os dois módulos usam os mesmos conceitos de status/source, autor/aprovador, revisão
concorrente, snapshot, bloqueios, arquivamento anterior por aluno, resposta null e
isolamento. Código explícito preserva a legibilidade; não foi criada abstração genérica
de planos. Diferenças são do domínio: duas camadas de filhos em Workout, frequência,
séries inteiras e prescrição textual, em vez de refeições/quantidades/substituições.

AI_GENERATED e PENDING_REVIEW permitem futuramente sugestões estruturadas, revisadas
pelo profissional antes de APPROVED. A interface manual não escolhe esses valores.
Não existe SDK, geração, envio externo de dados nem publicação automática por IA.
Uma futura biblioteca de exercícios poderá ser referenciada mantendo a cópia da
prescrição em cada snapshot; imagens, vídeos, equipamentos e grupos estruturados
exigirão escopo e migration próprios. Nada disso foi implementado preventivamente.

Débitos: paginação de planos/versões, suíte E2E persistente e proteção operacional
anterior à exposição pública. Não há execução em tempo real, concluir exercício,
cronômetro, registro/histórico de carga, progressão, records, volume, smartwatch,
notificações ou Evolution. O Dia 8 exige autorização específica.

Validação final do Dia 7: migration local 20260910_05 (head), Alembic check sem divergências,
backend e PostgreSQL saudáveis. Chrome headless com API real validou login, abertura do
aluno, criação de divisão/exercício, salvar/publicar, leitura Student, duplicação/edição,
histórico intacto antes de republicar e entrega da versão 2 ao aluno. MASTER somente leitura.
Editor e leitor foram testados em 1366, 1024, 768 e 375 px sem overflow horizontal ou
exceções JavaScript não tratadas. Capturas representativas dos quatro tamanhos foram
inspecionadas visualmente, incluindo instruções abertas em 375 px. Não há suíte E2E
persistente; os testes usaram schema e contas temporários, removidos ao terminar.
