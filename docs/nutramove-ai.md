# NutraMove AI — Dia 12

NutraMove AI cria sugestões assistidas de dieta e treino para revisão do Professional. É desabilitado por padrão. Para habilitar, configure `AI_ENABLED=true`, `AI_API_KEY` (segredo fora do Git), `AI_MODEL` e `AI_TIMEOUT_SECONDS` no ambiente do backend ou Compose. O backend envia `POST https://api.openai.com/v1/responses` via HTTPS, sem SDK novo, com `store=false` e JSON mode em `text.format.type=json_object`. O `input` solicita explicitamente JSON, como exigido pelo provider nesse modo, e preserva `context` e `output_schema` no objeto serializado. O JSON Schema segue no `input` como contrato para o modelo e a saída ainda é validada pelos schemas locais; o adapter atual não usa `json_schema` estrito. Nenhuma chamada paga é feita nos testes. Não há funcionalidade offline quando o provedor está indisponível.

A integração foi homologada localmente com chamada real e `AI_MODEL=gpt-5.6-luna`; isso não equivale a deploy público. O Professional inicia cada geração explicitamente. A chave permanece somente no backend e nunca integra o bundle ou variáveis públicas do frontend.

## Arquitetura e privacidade

`app/ai/provider.py` isola `generate_structured`; `app/ai/prompts.py` guarda as instruções `v1`; `app/ai/generation.py` monta contexto, valida e persiste. O contexto é construído campo a campo. Treino recebe objetivo, atividade, experiência, frequência e horário. Dieta recebe objetivo, atividade, horários, preferências e restrições. O Professional pode incluir orientações limitadas a 2.000 caracteres e optar por objetivo do plano atual e data/peso da última avaliação. O endpoint de contexto lista as categorias utilizadas antes do envio. Não são enviados nome do Student, e-mail, telefone, UUID, IP, credenciais, notificações, AuditLog, motivo de reavaliação, medidas, observações clínicas nem o perfil inteiro. Texto digitado pelo Professional e preferências/restrições podem conter dados sensíveis; configure o provedor e a política de tratamento adequadamente antes de habilitar.

O provedor retorna JSON, que é validado novamente pelos schemas `VersionContent` de dieta ou treino, com campos extras proibidos, limites de texto e listas e verificações de conteúdo mínimo. Saída inválida ou indisponibilidade não cria plano. Um filtro básico recusa termos explícitos de medicação, hormônios e cura garantida; ele não substitui avaliação clínica. Após a chamada externa, o backend relê Student com bloqueio e confirma carteira/status antes de criar um plano novo do Professional atual e versão 1 com `source=AI_GENERATED`, `status=PENDING_REVIEW`. Isso preserva os planos da carteira anterior. Não existe AIGeneration persistida, migration ou histórico de tentativas nesta V1; a versão já preserva origem e autor. Não há retry automático, fila, quota ou diagnóstico automatizado.

O Student não vê a versão pendente. O Professional pode editar no editor normal, preservando a origem, e aprovar pelo endpoint normal; a notificação de publicação ocorre somente nessa aprovação. A IA não arquiva nem substitui plano aprovado por conta própria. Os prompts proíbem diagnóstico, medicação e resultados garantidos, mas validação estrutural não comprova segurança clínica: revisão profissional continua obrigatória.

## API

- `GET /professional/ai/config`: retorna apenas `enabled`.
- `GET /professional/students/{id}/ai/plans`: informa os planos atuais da carteira para a ação conjunta.
- `POST /professional/students/{id}/ai/plans`: orquestra os geradores existentes de dieta e treino, preserva qualquer plano já existente e retorna falhas separadas por tipo.
- `GET /professional/students/{id}/ai/{diet|workout}/context`: nomes dos campos básicos disponíveis.
- `POST /professional/students/{id}/ai/diet` e `/workout`: `instructions`, `include_current_plan`, `include_recent_evolution`; retornam a versão pendente com HTTP 201.

A ação conjunta aparece na ficha de Student ACTIVE do Professional. Cada tipo ausente é gerado e confirmado independentemente; uma falha não remove o outro resultado. Consultas antes da chamada e uma nova verificação sob lock do Student impedem que repetição ou concorrência criem outro plano equivalente. Planos manuais, pendentes ou publicados nunca são sobrescritos. A interface apenas encaminha aos editores e à aprovação já existentes.

Autenticação e Origin seguem as rotas existentes. Apenas Professional da carteira atual gera. O provedor retorna 503 quando indisponível e 502 quando a resposta é inválida; o frontend oferece tentativa manual. A interface usa diálogo nativo, foco/teclado, estado ocupado, texto de progresso e link para o editor existente. O timeout do navegador é 65 segundos; ajuste o timeout do backend abaixo desse limite.

## Referência do provedor

A integração foi conferida contra [Responses API](https://platform.openai.com/docs/api-reference/responses/create) e [controles de retenção](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint). Não habilite sem revisar os termos de tratamento dos dados enviados.

Falhas do provider geram logs server-side com operação, modelo, categoria, status HTTP, tipo, código e parâmetro do erro quando disponíveis, classificação restrita da mensagem e timeout. A mensagem externa não é registrada: somente categorias fixas reconhecem problemas estruturais como parâmetro desconhecido ou não suportado. O logger não registra chave, header Authorization, prompt, payload, corpo completo da resposta ou dados do Student. A API continua retornando somente mensagens sanitizadas ao frontend.

## Prompt v2 e contexto ampliado

Na homologação corretiva, o Workout falhava na validação interna quando o prompt v2 gerava um dia de descanso com `exercises: []`. O contrato atual usa `isRest=true` para descanso e `isRest=false` para dia ativo; a classificação não depende do título ou descrição. O prompt e o output_schema incluem o flag, que é persistido e devolvido pela API. É exigido ao menos um dia ativo com exercícios. Uma falha estrutural registra apenas categoria, campo e tipo de validação, sem conteúdo da resposta ou dados do Student. Os testes usam provider falso; uma nova tentativa real pela interface ainda depende do Professional.

`PROMPT_VERSION=v2` incorpora a metodologia oficial para refeições, quantidades, acessibilidade, treino, descanso, volume, anti-redundância e tratamento conservador de limitações. O adapter preserva `store=false`, JSON mode e a palavra literal `JSON` no input.

Treino usa de um a seis dias ativos com exercícios. Dias não utilizados da semana são descanso implícito; um dia `isRest=true` e `exercises=[]` continua permitido quando houver motivo para representá-lo. O card de IA abre a versão para leitura e aprovação; o editor é opcional. Depois de uma reavaliação concluída com snapshot, a próxima geração usa os valores atualizados presentes nesse snapshot, cria versão nova e mantém as versões anteriores. Solicitações PENDING/IN_REVIEW não mudam o contexto, e nenhuma foto ou referência de armazenamento entra no provedor.

Diet recebe somente dados pertinentes à alimentação; Workout recebe somente dados pertinentes ao treino. Quando há snapshot de reavaliação concluída, seus valores atualizados prevalecem. Nome, e-mail, telefone, IDs, sessão, logs, notificações, fotos, URLs, caminhos e chaves de storage são excluídos. Contexto insuficiente deve produzir rascunho conservador com aviso no campo de observações suportado pelo schema.

A saída continua `AI_GENERATED` e `PENDING_REVIEW`, sem publicação ou notificação ao Student antes da aprovação do Professional.

## Exclusão de rascunhos na homologação

Professional da carteira atual pode excluir uma versão DRAFT ou PENDING_REVIEW de Diet ou Workout no detalhe, após confirmação. As refeições/alimentos/substituições ou dias/exercícios são removidos na mesma transação. O plano pai é removido apenas quando fica sem versões; versões publicadas e arquivadas permanecem protegidas (409). Após excluir a única versão, a ação conjunta de IA volta a considerar aquele tipo ausente, sem substituir o outro plano existente. O AuditLog atual registra apenas atribuição/transferência de Student e não representa exclusão de plano sem alteração do contrato e migration.

Um treino gerado anteriormente pode conter um dia vazio marcado como ativo e continuar bloqueado na aprovação. A correção do fluxo novo não reclassifica dados históricos: revise e edite o dia como descanso, ou exclua o rascunho e gere novamente. Nenhum registro local foi alterado automaticamente nesta correção.
