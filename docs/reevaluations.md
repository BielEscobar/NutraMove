# Solicitações de reavaliação — Dia 9

Implementado em 11 de setembro de 2026. A solicitação organiza o atendimento; não
modifica dieta, treino ou avaliações automaticamente.

## Modelo

`ReevaluationRequest` contém UUID, Student, Professional destinatário original,
categoria, motivo, status, resposta opcional, timestamps de criação/atualização,
início de análise, conclusão e cancelamento. Há responsáveis internos para início,
conclusão e cancelamento (`*_by_user_id`). São referências User da sessão que executou
a ação, sem aceitar valores do cliente. Não foi criada uma entidade AuditLog.

Enums são strings estáveis com constraints no banco, seguindo o padrão existente:

| Categoria | Rótulo |
| --- | --- |
| DIET | Dieta |
| WORKOUT | Treino |
| EVOLUTION | Evolução |
| DIFFICULTY | Dificuldade no acompanhamento |
| OTHER | Outro |

Motivo obrigatório com 10–2000 caracteres após trim. Resposta final obrigatória com
1–2000 caracteres após trim. Dados de entrada rejeitam campos extras. Não é possível
editar motivo, categoria ou resposta após o envio/conclusão por um endpoint genérico.

## Máquina de estados

| Origem | Ação | Destino | Quem |
| --- | --- | --- | --- |
| — | Criar | PENDING | Student ACTIVE, vinculado a profissional ativo. |
| PENDING | Iniciar análise | IN_REVIEW | Professional da carteira atual. |
| IN_REVIEW | Concluir com resposta | COMPLETED | Professional da carteira atual. |
| PENDING | Cancelar | CANCELLED | Student proprietário ou Professional da carteira. |
| IN_REVIEW | Cancelar | CANCELLED | Professional da carteira atual. |

COMPLETED e CANCELLED são finais. Transição incompatível retorna 409. Não se conclui
PENDING diretamente. Iniciar análise não exige resposta. Cancelamento registra instante
e responsável, sem exigir texto adicional. A UI solicita confirmação ao cancelar.

PENDING_APPROVAL e REJECTED podem consultar seu histórico, mas não enviar solicitações;
esta ação pertence ao acompanhamento já aprovado. Sem vínculo ou com profissional
inativo, o backend retorna 409 com explicação. User inativo não autentica.

## Concorrência

Existe no máximo **uma solicitação aberta por Student**, independente de categoria.
PENDING e IN_REVIEW são considerados abertos. Ao tentar outro envio, a API retorna 409:
“Você já possui uma solicitação de reavaliação em andamento.”

O serviço bloqueia Student/User antes de consultar/criar; transições seguem a ordem
Student/User → ReevaluationRequest, com releitura após bloqueio. O índice único parcial
`uq_reevaluation_open` em student_id, com condição `status IN ('PENDING', 'IN_REVIEW')`,
reforça a regra mesmo se uma inserção escapar do serviço. IntegrityError na criação
é tratado com rollback e mensagem de conflito. Há teste com duas conexões simultâneas.

Após conclusão ou cancelamento, outra solicitação pode ser criada. Não é um rate limiter:
limitação de abuso permanece dívida antes de exposição pública.

## Ownership e transferência futura

Student acessa exclusivamente solicitações do Student derivado do User autenticado.
Professional usa a carteira atual de Student.professional_id, filtrada no banco.
`ReevaluationRequest.professional_id` preserva quem recebeu originalmente a solicitação;
essa coluna isolada não concede acesso. MASTER consulta globalmente, sem ações de workflow.

Se um vínculo for transferido futuramente, sob esta regra o novo profissional poderá
consultar/atender o histórico e o anterior perderá acesso, sem reescrever o destinatário
original. O teste simula alteração direta do vínculo apenas para verificar autorização.
Transferência não foi implementada e deve revisar essa política e concorrência quando
receber um fluxo administrativo próprio.

Acesso a solicitação alheia e ID inexistente retorna 404, inclusive nas mutações.
Filtro staff por student_id passa pelo mesmo ownership antes da busca.
Anônimo recebe 401, role inadequada 403. Student não pode responder; MASTER não pode
responder em nome de Professional. UI não substitui essas verificações.

## Endpoints

| Perfil | Método / rota | Finalidade |
| --- | --- | --- |
| Student | POST /student/reevaluation-requests | Criar própria solicitação; 201. |
| Student | GET /student/reevaluation-requests | Listar histórico próprio. |
| Student | GET /student/reevaluation-requests/{id} | Consultar motivo, resposta e datas. |
| Student | POST /student/reevaluation-requests/{id}/cancel | Cancelar PENDING. |
| Professional | GET /professional/reevaluation-requests | Listar carteira. |
| Professional | GET /professional/reevaluation-requests/{id} | Consultar detalhe. |
| Professional | POST /professional/reevaluation-requests/{id}/start-review | Iniciar análise. |
| Professional | POST /professional/reevaluation-requests/{id}/complete | Concluir com professional_response. |
| Professional | POST /professional/reevaluation-requests/{id}/cancel | Cancelar solicitação aberta. |
| MASTER | GET /master/reevaluation-requests | Listar globalmente. |
| MASTER | GET /master/reevaluation-requests/{id} | Consultar detalhe. |

Listagens: status e category opcionais; staff também aceita student_id. Paginação
padrão 20, máximo 100, ordenação created_at e UUID decrescentes. Listas retornam motivo
resumido em 160 caracteres; detalhes retornam motivo e resposta completos. Nenhuma
listagem retorna a resposta completa, senha, token ou identificadores de autoria.

Schema Student omite student_id/professional_id e autores internos. Schema staff
acrescenta apenas student_id e student_name para identificação e navegação.
As respostas bem-sucedidas usam no-store. Mutações validam Origin; CORS permanece
GET/POST/PATCH. SafeErrorMiddleware e hide_parameters permanecem ativos.

## Dashboard, frontend e consultas

Dashboard Professional acrescenta `reevaluations_pending` e `reevaluations_in_review`.
COUNT/FILTER são executados no banco dentro do escopo de Student; nenhuma coleção
completa é carregada para contar. Índices status e (student_id, created_at), além do
índice parcial, atendem as consultas. Não foi criado índice no destinatário histórico,
pois o acesso atual consulta Student.professional_id, já indexado.

Student possui menu Solicitar reavaliação, formulário, histórico e detalhe da resposta.
Professional possui menu Reavaliações, filtros status/categoria, detalhe e somente as
ações válidas. MASTER utiliza consulta equivalente sem editor. Links de dieta, treino
e evolução levam às páginas existentes do aluno. Não há busca textual adicional nesta
etapa; filtro por student_id está disponível na API staff.

Mensagens 409 destes endpoints são exibidas pelo cliente HTTP a partir do erro estruturado
do backend, permitindo explicar duplicidade e pré-requisitos. Conteúdo é renderizado como
texto React, sem HTML injetado. Formulários usam labels, limites, estado ocupado e guarda
contra duplo envio; erros/sucesso são anunciados. Status não depende exclusivamente de cor.

## Arquivos e limites

Backend: models/reevaluation.py, schemas/reevaluation.py, repositories/reevaluations.py,
services/reevaluations.py, api/reevaluations.py e tests/test_reevaluations.py.
Integração: models/__init__.py, main.py, api/dashboards.py, schemas/dashboard.py e
ajuste do limite de consultas no teste existente de dashboard para incluir as contagens.
Frontend: lib/reevaluations.ts, components/reevaluations/*, páginas reevaluation-requests
por perfil, AppShell, lib/api.ts, lib/dashboard.ts e ManagementDashboard.
Migration compartilhada `20260911_07` depende da revisão real anterior `20260911_06`.

Não há notificações, e-mail, WhatsApp, cron, AI, alteração automática de planos,
transferência ou auditoria geral. O Professional deve visitar dashboard/listagem;
não há polling. Timestamps permitem futura integração explícita com notificações,
mas nenhuma etapa do Dia 10 foi iniciada. Testes E2E ainda não formam uma suíte persistente.

Veja [validation.md](validation.md) e [dia9-relatorio.md](dia9-relatorio.md).

## Anamnese v2 e snapshots

A criação oficial pela interface exige um snapshot atual e novas fotos FRONT/SIDE. O snapshot JSONB é validado e imutável: conserva peso, objetivo, atividade, disponibilidade, percepção de evolução, dificuldades, observações e campos opcionais que mudaram. Ele não sobrescreve a anamnese inicial. O lifecycle PENDING → IN_REVIEW → COMPLETED e cancelamentos existentes permanece igual.

A NutraMove AI usa o snapshot mais recente com status COMPLETED quando existe; caso contrário usa o estado atual da anamnese. Fotos e referências de storage nunca entram no contexto.

Na homologação final, a interface passou a oferecer seis etapas: evolução/objetivo, rotina/treino, alimentação, saúde/limitações, fotos e revisão. Ela preenche os campos com a última reavaliação concluída, quando disponível, ou com o cadastro atual. O Student pode confirmar ou alterar os dados sem redigitar tudo; voltar de etapa preserva o rascunho. O snapshot enviado conserva os valores daquele momento, inclusive campos que foram limpos. Solicitações PENDING ou IN_REVIEW não alteram o contexto da IA.
