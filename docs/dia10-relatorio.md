# Dia 10 — Informativos e notificações internas

Data: 13 de setembro de 2026.

## 1. Resumo e estado inicial

Implementados informativos publicados por Professional e inbox interna de Notification por User. O início foi na branch develop, com trabalho local do Dia 10 já presente; nenhuma alteração local foi descartada. A revisão em código era 20260912_08, dependente de 20260911_07. O banco local ainda estava em 20260911_07 antes do upgrade. Nenhum commit foi criado.

## 2. Arquivos criados

Backend: migration `20260912_08_informations_notifications.py`; models, schemas, repositories, services e APIs de `information` e `notification`; testes `test_informations.py` e `test_notifications.py`.

Frontend: `src/lib/informations.ts` e `notifications.ts`; componentes de lista e detalhe de informativos, editor Professional, sino e inbox; rotas de informativos para Professional, Student e MASTER e rota compartilhada `/notifications`.

Documentação: `docs/informations.md`, `docs/notifications.md` e este relatório.

## 3. Arquivos modificados

Backend: `app/main.py`, `models/__init__.py` e services de Diet, Workout, Student e Reevaluation para registrar routers/models e emitir eventos. Frontend: `app-shell.tsx` e `use-api-resource.ts`. Documentação: README, architecture, validation e relatorio-contexto-proximos-prompts.

## 4. Information, audiência, status e ownership

Information tem UUID, Professional, Student opcional, título, conteúdo, categoria enum, status, revisão de edição, data de publicação, autor e timestamps. Student nulo significa toda a carteira; Student preenchido significa audiência individual. O Professional vem da sessão e a audiência individual é validada no backend. Estados: DRAFT, PUBLISHED e ARCHIVED. Somente rascunho é editável; atualização e transição exigem `expected_revision`. Publicação cria notificações na mesma transação. Não há exclusão física nem versionamento de conteúdo.

Professional lista, cria, consulta, edita, publica e arquiva sob `/professional/informations`. Student lista e consulta somente publicados da carteira atual, gerais ou individuais próprios, sob `/student/informations`. MASTER lista e consulta sob `/master/informations`, sem mutações. Listagens são paginadas e filtráveis. Recursos alheios retornam 404.

## 5. Frontend de informativos

Professional possui navegação, lista, filtros por status/categoria/público geral, editor para audiência geral ou Student próprio, salvar rascunho, publicar e arquivar. A seleção individual pesquisa alunos ACTIVE da própria carteira em páginas de até 20 resultados, sem lista pública global. Student vê cards com categoria textual, data, resumo e conteúdo completo. MASTER tem leitura administrativa. A interface usa AppShell existente e layouts responsivos.

## 6. Notification, eventos, transações e leitura

Notification pertence a User, com tipo enum, título, mensagem curta fixa, recurso tipado, read_at e timestamps. Eventos integrados: DietVersion e WorkoutVersion aprovadas; ReevaluationRequest criada, iniciada, concluída e cancelada por Professional; Information publicada; Student vinculado pendente de aprovação. Nenhum evento é emitido para draft/edição comum. A criação ocorre na transação da mutação. Publicação geral usa INSERT SELECT para Students ACTIVE com User ativo. Restrição única por destinatário/tipo/recurso evita duplicidade.

`GET /notifications` pagina e filtra não lidas; `GET /notifications/unread-count` usa SQL COUNT; `GET /notifications/{id}`, `POST /notifications/{id}/read` e `POST /notifications/read-all` aplicam user_id da sessão. MASTER não lê inbox alheia. AppShell exibe sino com badge e rótulo acessível; a inbox exibe estado textual, ações e links mapeados somente para tipos conhecidos.

## 7. IDOR, privacidade e acessibilidade

Os novos testes cobrem isolamento de informativos e inbox, perfis, Origin, validação, transições, eventos e rollback. Notification não copia motivo de reavaliação, conteúdo de planos, informativo inteiro ou dados físicos; não recebe URL arbitrária. Interfaces usam labels, texto para status, foco dos controles existentes e alvos de toque de pelo menos 44 px. Não foi executada auditoria WCAG completa.

## 8. Migration e testes

Migration 20260912_08 cria `informations` e `notifications`, FKs, checks, índices e unicidade. A suíte de testes usa PostgreSQL em schemas temporários e testa upgrade, downgrade, novo upgrade e Alembic check. Suíte completa: **373 passaram**, nenhum pulado; aviso interno Starlette/AnyIO conhecido. Ruff check/format, mypy strict (102 arquivos), pip check, Biome (127 arquivos), TypeScript e build Next.js passaram. Compose config e build Docker passaram. O upgrade local foi executado: Alembic current confirmou 20260912_08 (head) e check não detectou operações novas.

## 9. Validação funcional, visual e limites

Os testes exercitam API real com PostgreSQL temporário, inclusive fluxos de publicação, inbox, permissões e eventos. Não houve automação de navegador nem inspeção visual nesta execução; por isso as larguras 1366/1024/768/375 px e o fluxo completo no Chrome permanecem sem confirmação visual. O backend local reiniciado respondeu /health 200; as rotas novas, sem sessão, retornaram 401. O build compilou todas as novas rotas. Não há push, e-mail, SMS, WhatsApp, cron, IA ou transferência.

## 10. Preparação para Dia 11

Transferência de Student deverá definir leitura de Information da carteira antiga e destino de informativos individuais. Notification permanece no User; links a recursos antigos podem deixar de ser acessíveis após transferência e devem seguir a política futura. Diet, Workout, Assessment, Hydration e Reevaluation preservam histórico; nenhuma transferência ou AuditLog foi implementado neste Dia.
