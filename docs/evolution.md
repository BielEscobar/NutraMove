# Evolução física e avaliações — Dia 8

Implementado em 11 de setembro de 2026. Sem IA, hidratação, workflow de reavaliação,
notificações, diagnóstico ou alterações automáticas de Diet/Workout.

## Modelos e decisão de histórico

Assessment é o evento principal. Não há WeightRecord separado: seria redundante nesta V1.
Uma avaliação pode registrar peso, altura, medidas e observações. Student.weight é o valor
atual conveniente para perfil/dashboard; Assessment é a fonte histórica de avaliações.
Nenhum registro foi criado automaticamente a partir do peso do onboarding.

Relações: Student 1:N Assessment; Professional 1:N Assessment; Assessment 1:N Measurement.

Assessment contém UUID, student_id/professional_id obrigatórios, assessment_date, weight_kg,
height_cm, notes, created_by_user_id, updated_by_user_id, created_at, updated_at e edit_revision.
Measurement contém UUID, assessment_id, measurement_type, side opcional, value_cm e notes.
Filhos não possuem timestamps próprios: seguem a correção atômica e timestamps da avaliação.
FKs de identidade usam RESTRICT; medidas usam CASCADE e delete-orphan. Não há DELETE na API.

measurement_type é enum controlado: ARM, CHEST, WAIST, ABDOMEN, HIP, THIGH e CALF.
LEFT/RIGHT são permitidos apenas para braço, coxa e panturrilha. Side nulo significa
não especificado. Não misturar medida sem lado com medidas laterais do mesmo tipo na
avaliação. Tipo/lado duplicado é rejeitado. UNIQUE com NULLS NOT DISTINCT também protege
as medidas sem lado no PostgreSQL 17, além dos CHECKs de valor e lateralidade.

## Validação, datas e correção

Valores são números finitos entre 0,1 e 10000, em kg/cm. Limites técnicos amplos não são
recomendações clínicas. Pelo menos um peso, altura, medida ou observação deve ser informado.
Notas da avaliação: até 4000 caracteres; notas de cada medida: até 1000; até 13 medidas
no payload. A combinação de tipos/lados válidos permite no máximo dez medidas simultâneas.
Campos extras, identidade, autoria e IDs de medidas enviados pelo cliente são rejeitados.

assessment_date é independente de created_at e permite lançamento retroativo, mas não
futuro em relação à data do servidor. Datas da avaliação são civis; timestamps usam UTC.
Edição não aceita assessment_date, student_id ou professional_id.

PATCH recebe o conteúdo completo (peso, altura, notas e medidas) e expected_revision.
Não é uma edição parcial de campos omitidos. A data e criação são preservadas; atualização,
autor da correção e revisão mudam. Revisão obsoleta retorna 409. Não há versionamento
completo como Diet/Workout: a rastreabilidade desta V1 indica criação e última correção,
sem armazenar valores anteriores da mesma avaliação. O histórico entre avaliações permanece.
Uma data lançada incorretamente ainda não possui fluxo de correção nesta V1.

Um peso já registrado pode ser corrigido, mas não removido. Isso evita perder a última
fonte histórica sem armazenar um peso-base redundante. Avaliações novas podem não ter peso;
é possível adicioná-lo depois. Altura pode ser corrigida ou removida, recalculando o IMC
somente daquela avaliação. Não há altura herdada implicitamente do perfil.

## Peso atual e atomicidade

A avaliação mais recente COM peso é escolhida por:
1. assessment_date descendente;
2. created_at descendente;
3. UUID descendente como desempate estável.

Após criar/corrigir uma avaliação, o serviço consulta essa fonte e sincroniza Student.weight
na mesma transação. Criar um registro retroativo ou corrigir peso antigo não substitui o
peso mais recente. Exemplo: A=80 em 01/09, B=82 em 10/09; corrigir A para 79 mantém 82;
corrigir B para 81 atualiza o perfil para 81. Avaliações sem peso não apagam a série.
Sem qualquer peso histórico, o perfil mantém o valor de onboarding, e a evolução informa
peso histórico indisponível. Não apresenta onboarding como avaliação inventada.

O serviço bloqueia Student/User antes de alterar a avaliação. Falhas na gravação ou na
sincronização desfazem tudo, inclusive medidas. O formulário de perfil continua disponível,
mas, quando existe peso histórico, tentativa de alterar weight por essa rota retorna 409,
orientando a correção em Evolução. Esse pequeno ajuste evita divergência entre as fontes.
Student.height permanece independente; a avaliação registra sua própria altura.

## IMC de referência

Calculado no backend como weight_kg / (height_cm / 100)², arredondado a duas casas.
Não há coluna BMI no banco. Peso e altura devem existir no mesmo snapshot; caso contrário,
bmi é null. Mudanças posteriores de altura do perfil não recalculam avaliações anteriores.
O resumo atual usa o IMC da avaliação escolhida como fonte do peso atual; não combina
peso de uma data com altura de outra. Nenhuma classificação clínica é implementada.

A interface apresenta: “Indicador de referência calculado a partir do peso e altura
registrados. Não é um diagnóstico.” O campo calculado usa computed_field do Pydantic;
a exceção local de tipagem prop-decorator documenta a limitação do mypy para esse decorator.

## Ownership, IDOR/BOLA e privacidade

Professional é derivado do User autenticado. O escopo reutiliza o repository Student,
exige aluno da carteira e consistência com Assessment.professional_id. Recursos alheios
e inexistentes retornam 404 em consultas e mutações. Anônimo recebe 401 e perfil
inadequado recebe 403. Mutações exigem Origin confiável. IDs não concedem autorização.

Student consulta somente os próprios registros, inclusive no detalhe por UUID. Query
student_id não troca identidade. Contas autenticadas com cadastro pendente/rejeitado
podem consultar seus próprios registros, como no perfil; não há publicação de avaliações.
MASTER consulta administrativamente e não possui rotas de criação/correção.

Schemas Student omitem autoria interna, vínculo e revisão de edição. Listagem não expõe
notas nem medidas detalhadas. Evolution seleciona colunas necessárias aos gráficos, sem
retornar objetos administrativos completos. Observações são visíveis ao aluno: não são
anotações privadas. Preservados sessão opaca, middleware seguro, hide_parameters e logs
sem conteúdo pessoal. Não há envio externo ou dumps JSON de perfil para IA.

## Schemas, repositories e services

MeasurementInput, AssessmentContent/Create/Update validam o payload. AssessmentBrief,
AssessmentResponse e StaffAssessmentResponse separam listagem, leitura do aluno e staff.
AssessmentList é paginado. EvolutionResponse contém current, weight_history, bmi_history,
measurements (uma série por tipo/lado) e period; pontos contêm somente ID, data e valor.

Repositories aplicam ownership, ordenação, paginação, filtro temporal e projeções para
séries. Services controlam criação, correção, revisão e sincronização de peso. Routers
reutilizam dependências de identidade, perfil e no-store, sem duplicar autenticação.

## Endpoints

| Perfil | Método | Rota |
| --- | --- | --- |
| PROFESSIONAL | GET, POST | /professional/students/{student_id}/assessments |
| PROFESSIONAL | GET, PATCH | /professional/assessments/{assessment_id} |
| PROFESSIONAL | GET | /professional/students/{student_id}/evolution |
| MASTER | GET | /master/students/{student_id}/assessments |
| MASTER | GET | /master/assessments/{assessment_id} |
| MASTER | GET | /master/students/{student_id}/evolution |
| STUDENT | GET | /student/assessments |
| STUDENT | GET | /student/assessments/{assessment_id} |
| STUDENT | GET | /student/evolution |

Criação retorna 201; leituras e correções, 200; validação, 422; conflitos, 409.
Listas: page padrão 1, page_size padrão 20 e máximo 100, com total e ordem estável.
Evolution: period padrão 90d; aceita 7d, 30d, 90d, 6m, 1y e all. Filtro é executado no SQL
sobre assessment_date. Períodos em dias incluem hoje e os N−1 dias anteriores; meses/ano
subtraem meses de calendário, ajustando o dia ao último dia válido do mês, limite inclusivo.
O resumo current considera todo o histórico; o filtro altera somente as séries.
Histórico paginado da tela é completo, independente do período do gráfico, e está rotulado.

Sem avaliações: current=null e séries vazias. Com avaliação apenas de notas/medidas:
última data é real, mas peso/IMC permanecem null. Pontos na mesma data não são agregados
nem descartados; mantêm o desempate estável. all ainda não tem limite/agregação de pontos.

## Frontend e gráficos

Professional: Meus alunos → aluno → Evolução → Nova avaliação. Formulário com data,
peso, altura, medidas opcionais e lateralidade, observações, validação, loading, erros e
proteção contra envio duplicado. Detalhe apresenta medidas e timestamps e oferece Corrigir
avaliação, preservando a data. Saída pelo link Voltar ou fechamento avisa sobre alterações.

Student: Minha evolução na navegação e resumo no dashboard, com dados reais ou estado
vazio. Peso/IMC, última avaliação, gráfico, histórico e detalhe são somente leitura.
MASTER usa as mesmas telas de leitura sem ações de cadastro/correção.

Recharts 3.10.1 foi adicionado após verificar package.json e peerDependencies compatíveis
com React 19. package-lock.json foi atualizado; instalação reportou zero vulnerabilidades.
A dependência atende ao gráfico responsivo com tooltip e suporte de acessibilidade,
evitando implementar manualmente eixos/interação. Documentação consultada:
[LineChart](https://recharts.github.io/en-US/api/LineChart/) e
[ResponsiveContainer](https://recharts.github.io/en-US/api/ResponsiveContainer/).

Gráfico mostra peso ou uma medida/lado por vez, linhas retas, pontos, tooltip, datas e
alternativa textual. Sem suavização, polling, dados fictícios, diagnóstico ou dashboard
analítico adicional. Não existe gráfico de sete linhas concorrentes. IMC tem série na API,
mas a interface V1 mostra o indicador de referência e o histórico por avaliação.

## Arquivos

Criados backend:
- app/models/assessment.py: Assessment, Measurement e enums.
- app/schemas/assessment.py: validação, respostas e cálculo de IMC.
- app/repositories/assessments.py: escopo, histórico, períodos e séries.
- app/services/assessments.py: transações e peso atual.
- app/api/assessments.py: rotas dos três perfis.
- tests/test_assessments.py: 33 testes, incluindo parametrizações.
- alembic/versions/20260911_06_assessments.py: duas tabelas, FKs, índices e constraints.

Modificados backend: app/main.py e app/models/__init__.py para registro; services/students.py
para impedir alteração de peso pelo perfil quando há fonte histórica.

Criados frontend:
- src/lib/evolution.ts: contratos, rótulos e apresentação de números/datas.
- components/evolution/{assessment-form,assessment-detail,evolution-page,evolution-chart,
  evolution-summary}.tsx.
- professional/students/[id]/evolution e assessments/new.
- professional/assessments/[id] e edit.
- master/students/[id]/evolution e master/assessments/[id].
- student/evolution e student/assessments/[id].

Modificados frontend: package.json/package-lock.json; components/app-shell.tsx;
components/students/student-detail.tsx e app/student/page.tsx. Documentação atualizada:
README, architecture, validation e relatorio-contexto-proximos-prompts. A alteração local
pré-existente em docs/workouts.md foi preservada; código de Diet/Workout não foi alterado.

## Migration e qualidade

HEAD inicial confirmado no código e banco: 20260910_05. Nova revisão 20260911_06 depende
dele; nenhuma migration anterior foi editada. Upgrade/downgrade/upgrade/check passaram
nas fixtures PostgreSQL isoladas. Banco local atualizado para 20260911_06 (head), Alembic
check sem divergências, backend e banco saudáveis. Compose config e build Docker aprovados.

293 testes passaram, nenhum pulado, incluindo 33 específicos. Cobrem ownership/IDOR,
campos injetados, lateralidade, validação, períodos, IMC, datas retroativas, ordenação,
correções antigas/atuais, perfil, atomicidade, Student próprio, MASTER read-only e Origin.
Ruff check/format, mypy strict (75 arquivos) e pip check aprovados. Permanece o aviso
interno Starlette/AnyIO sobre BlockingPortal, não ocultado.

## Limites e futuro

Não há auditoria de valores anteriores de uma correção, exclusão, correção de data,
remoção de peso já registrado ou histórico de alterações manuais anteriores do perfil.
Retenção, privacidade/LGPD e procedimentos de correção mais amplos exigem escopo próprio.
all pode crescer: avaliar agregação/limites conforme volume; sem cache complexo nesta V1.
A suíte E2E persistente continua pendente. Requisitos operacionais de produção anteriores
(proteção contra abuso, HTTPS, backup, observabilidade) permanecem.

Campos estruturados permitem selecionar futuramente datas, pesos e medidas relevantes
para revisão profissional de planos. Não há ai_context_json, assessment_json, dump de
Student, integração IA, hidratação, reavaliação automatizada, fotos, gordura corporal,
bioimpedância, recomendações, alterações de Diet/Workout ou integrações de dispositivos.
Dia 9 não foi implementado nem autorizado automaticamente.

## Validação final do Dia 8

- pytest: 293 passaram, nenhum pulado; 33 específicos de avaliações.
- Ruff check e format: aprovados; mypy strict: 75 arquivos sem erros; pip check aprovado.
- Biome: 97 arquivos aprovado; TypeScript e build Next.js finais aprovados.
- Compose config --quiet, build Docker, Alembic current/check aprovados.
- Banco local em 20260911_06 (head); backend/PostgreSQL saudáveis; /health 200,
  /student/evolution anônimo 401. Upgrade/downgrade/upgrade/check em schemas isolados.
- Chrome headless e API real: estado vazio, duas avaliações, peso/altura/medida, gráfico,
  filtro de período, tooltip, série de cintura, correção antiga preservando peso atual e
  data, dashboard/consulta Student e consulta MASTER sem edição passaram.
- Formulário, gráfico, histórico e medidas testados em 1366/1024/768/375 px sem overflow
  horizontal. Capturas representativas inspecionadas; formulário e gráfico legíveis em
  375 px. Nenhuma exceção JavaScript não tratada. Uma captura antecipada do gráfico foi
  repetida após estabilizar o redimensionamento, confirmando SVG e pontos nos quatro tamanhos.
- Testes de navegador usaram contas/schema temporários, removidos ao terminar. Não há
  suíte E2E persistente. Contas demo e registros reais existentes foram preservados.

Problemas encontrados: um comando de edição usou caminho relativo incorreto, corrigido
sem alterar arquivo errado; ajustes de importação/tipagem e semântica ARIA foram corrigidos.
Mypy exige exceção local prop-decorator para computed_field sobre property do Pydantic.
O build final encontrou EPERM em .next no Windows; após encerrar o dev temporário e
remover somente os artefatos gerados desse diretório verificado, o build passou.
Permanece apenas o DeprecationWarning interno Starlette/AnyIO já conhecido.
