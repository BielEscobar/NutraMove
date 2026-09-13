# NutraMove AI — Dia 12

NutraMove AI cria sugestões assistidas de dieta e treino para revisão do Professional. É desabilitado por padrão. Para habilitar, configure `AI_ENABLED=true`, `AI_API_KEY` (segredo fora do Git), `AI_MODEL` e `AI_TIMEOUT_SECONDS` no ambiente do backend ou Compose. O backend usa a Responses API da OpenAI via HTTPS, sem SDK novo, com `store=false` e saída JSON. Nenhuma chamada paga é feita nos testes. Não há funcionalidade offline quando o provedor está indisponível.

## Arquitetura e privacidade

`app/ai/provider.py` isola `generate_structured`; `app/ai/prompts.py` guarda as instruções `v1`; `app/ai/generation.py` monta contexto, valida e persiste. O contexto é construído campo a campo. Treino recebe objetivo, atividade, experiência, frequência e horário. Dieta recebe objetivo, atividade, horários, preferências e restrições. O Professional pode incluir orientações limitadas a 2.000 caracteres e optar por objetivo do plano atual e data/peso da última avaliação. O endpoint de contexto lista as categorias utilizadas antes do envio. Não são enviados nome do Student, e-mail, telefone, UUID, IP, credenciais, notificações, AuditLog, motivo de reavaliação, medidas, observações clínicas nem o perfil inteiro. Texto digitado pelo Professional e preferências/restrições podem conter dados sensíveis; configure o provedor e a política de tratamento adequadamente antes de habilitar.

O provedor retorna JSON, que é validado novamente pelos schemas `VersionContent` de dieta ou treino, com campos extras proibidos, limites de texto e listas e verificações de conteúdo mínimo. Saída inválida ou indisponibilidade não cria plano. Um filtro básico recusa termos explícitos de medicação, hormônios e cura garantida; ele não substitui avaliação clínica. Após a chamada externa, o backend relê Student com bloqueio e confirma carteira/status antes de criar um plano novo do Professional atual e versão 1 com `source=AI_GENERATED`, `status=PENDING_REVIEW`. Isso preserva os planos da carteira anterior. Não existe AIGeneration persistida, migration ou histórico de tentativas nesta V1; a versão já preserva origem e autor. Não há retry automático, fila, quota ou diagnóstico automatizado.

O Student não vê a versão pendente. O Professional pode editar no editor normal, preservando a origem, e aprovar pelo endpoint normal; a notificação de publicação ocorre somente nessa aprovação. A IA não arquiva nem substitui plano aprovado por conta própria. Os prompts proíbem diagnóstico, medicação e resultados garantidos, mas validação estrutural não comprova segurança clínica: revisão profissional continua obrigatória.

## API

- `GET /professional/ai/config`: retorna apenas `enabled`.
- `GET /professional/students/{id}/ai/{diet|workout}/context`: nomes dos campos básicos disponíveis.
- `POST /professional/students/{id}/ai/diet` e `/workout`: `instructions`, `include_current_plan`, `include_recent_evolution`; retornam a versão pendente com HTTP 201.

Autenticação e Origin seguem as rotas existentes. Apenas Professional da carteira atual gera. O provedor retorna 503 quando indisponível e 502 quando a resposta é inválida; o frontend oferece tentativa manual. A interface usa diálogo nativo, foco/teclado, estado ocupado, texto de progresso e link para o editor existente. O timeout do navegador é 65 segundos; ajuste o timeout do backend abaixo desse limite.

## Referência do provedor

A integração foi conferida contra [Responses API](https://platform.openai.com/docs/api-reference/responses/create) e [controles de retenção](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint). Não habilite sem revisar os termos de tratamento dos dados enviados.