# Dia 12 — Relatório de implementação

Data: 13 de setembro de 2026. Estado do código local, sem commit/push.

## 1. Resumo

NutraMove AI gera sugestões estruturadas de Diet e Workout para Student ativo da carteira do Professional. Cada resultado cria um plano normal novo, com versão 1 `AI_GENERATED/PENDING_REVIEW`. Student só vê o plano após edição/revisão e aprovação pelo fluxo normal. A funcionalidade fica desabilitada por padrão.

## 2. Git e Alembic inicial

Branch `develop`, working tree limpo; nenhuma alteração preexistente. HEAD e banco local: `20260913_09`. A documentação dos Dias 6–11 e os modelos, schemas, services, repositories e telas de Diet, Workout, Student, Evolution, Reevaluation, Professional, Notification e AuditLog foram inspecionados antes da implementação. Não houve nova migration nem mudança no schema.

## 3. Arquitetura e provider

`app/ai/provider.py` define `generate_structured` e adapta HTTPS à Responses API; o restante do domínio depende do protocolo, permitindo fake nos testes. `prompts.py` centraliza instruções `v1`. `generation.py` monta contexto explícito, verifica permissões, chama o provedor, valida a saída e cria o plano. O provedor usa `store=false`, JSON, timeout configurável e não registra payload nem resposta. Não há SDK ou dependência nova. A integração externa real não foi chamada nesta validação, pois não foi fornecida configuração de cobrança/segredo.

## 4. Configuração e disponibilidade

`AI_ENABLED=false`, `AI_API_KEY`, `AI_MODEL=gpt-4o-mini` e `AI_TIMEOUT_SECONDS=45` foram adicionados à configuração e aos exemplos de ambiente, inclusive Compose. Chave é `SecretStr` e fica apenas no backend. `GET /professional/ai/config` informa só `enabled`; quando desabilitado, o frontend esconde a ação e Diet/Workout manuais continuam. O timeout de requisição no navegador é 65 segundos.

## 5. Arquivos criados

`backend/app/ai/{__init__,provider,prompts,generation,safety}.py`, `backend/app/api/ai.py`, `backend/tests/test_ai.py`, `frontend/src/components/ai/ai-generator.tsx`, `docs/nutramove-ai.md` e este relatório.

## 6. Arquivos modificados

`backend/app/core/config.py`, `backend/app/main.py`, `backend/.env.example`; `frontend/src/components/diets/{diet-list,version-detail}.tsx`, `frontend/src/components/workouts/{workout-list,version-detail}.tsx`; `infra/compose.yaml`, `infra/.env.example`; `README.md`, `docs/architecture.md`, `docs/validation.md` e `docs/relatorio-contexto-proximos-prompts.md`. `frontend/next.config.ts` e `tsconfig.json` foram alterados temporariamente só para validar build em diretório alternativo e restaurados; o artefato temporário foi removido.

## 7. Rastreabilidade e migration

Não foi criada AIGeneration: na operação síncrona V1, a versão já registra source, status, criador e datas. Falhas externas não persistem tentativa ou contexto. É uma limitação explícita para observabilidade e histórico de falhas. Alembic permanece em `20260913_09`; `check` sem operações novas. Não foi expandido AuditLog de atribuições/transferências.

## 8. Contexto mínimo Workout

Objetivo/detalhe, nível de atividade, experiência, frequência e horário preferido. Opcionalmente, objetivo do último treino aprovado e data/peso da última avaliação. Orientações do Professional são limitadas a 2.000 caracteres e passam por trim.

## 9. Contexto mínimo Diet

Objetivo/detalhe, atividade, horários, preferências e restrições alimentares. Opcionalmente, objetivo da dieta aprovada e data/peso da última avaliação. Não são geradas macros ou calorias fictícias fora do domínio.

## 10. Dados não enviados e prompts

Não são enviados nome do Student, e-mail, telefone, UUID, IP, cookies, senha, tokens, notificações, motivo de reavaliação, AuditLog, medições completas, observações clínicas ou dump do perfil. O texto livre do Professional e preferências/restrições podem conter dados sensíveis; isso exige governança antes de ativar o provedor externo. Prompt `v1` exige JSON, sinalização de contexto insuficiente nas notas e proíbe diagnóstico, medicação, cura e promessa de resultado. Um filtro adicional recusa termos médicos explicitamente fora do escopo; não constitui auditoria clínica.

## 11. Geração e saída estruturada

`POST /professional/students/{id}/ai/diet` e `/workout` recebem opções de plano/evolução e orientações. O contexto básico pode ser consultado antes via `GET .../context`. A resposta do provedor é validada pelos mesmos `VersionContent` Pydantic usados no editor, com campos extras proibidos, limites e ao menos uma refeição/alimento ou divisão/exercício. Saída inválida retorna 502; indisponibilidade 503. Não há retry automático, fila ou polling; o usuário pode tentar de novo.

## 12. Atomicidade, ownership e transferência

A chamada externa ocorre antes da escrita. Após ela, Student é relido sob lock, status ACTIVE e carteira são verificados novamente. O plano e toda a árvore da versão são gravados em uma transação. Falha não deixa plano parcial; edição do plano aprovado não ocorre. Outro Professional recebe 404. Após transferência, o antigo perde permissão e o novo cria plano em seu próprio nome; planos antigos continuam históricos. A criação de plano novo elimina disputa pela numeração de versões do mesmo plano, mas duas requisições distintas ainda podem produzir duas sugestões separadas.

## 13. Revisão, aprovação e Notification

Versões geradas permanecem PENDING_REVIEW e editáveis pelo editor normal; a origem AI_GENERATED permanece após edição. A aprovação usa o endpoint normal de Diet/Workout, arquiva o plano aprovado anterior e cria a Notification já existente uma única vez. Não há aviso ao Student quando a IA gera o rascunho. Student não possui rota de geração e não consulta versão pendente. MASTER não gera. Não foi adicionado status REJECTED ou publicação automática.

## 14. Frontend, UX e acessibilidade

As listas profissionais de dieta e treino oferecem diálogo NutraMove AI com resumo dos campos, opções de plano/evolução, textarea, aviso de revisão, estado ocupado, prevenção de duplo clique, timeout, erro seguro, tentativa manual e link para o editor existente. A lista atualiza após sucesso. Detalhes de versões mostram origem e aviso de revisão. Diálogo nativo, labels, foco, texto de feedback, status/alert e alvos de 44 px foram usados. Não equivale a auditoria WCAG.

## 15. IDOR/BOLA e privacidade

Cookie, papel e Origin seguem a API. Anônimo recebe 401, papel inadequado 403, Student de outra carteira 404. O contexto enviado ao fake nos testes não contém PII desnecessária. Erros do provedor são convertidos em mensagens seguras; stack trace, key e resposta bruta não aparecem na API. Não foi feito envio a provedor pago na validação.

## 16. Testes e qualidade

Testes novos: 7, com sucesso de Diet/Workout, edição, aprovação, invisibilidade inicial para Student, notificação, IDOR, transferência, saída inválida, configuração desabilitada, anônimo e filtro de conteúdo médico. Testes usam PostgreSQL em schemas temporários e fake na fronteira do provedor. Total da suíte final: 397 testes passaram, nenhum pulado. Ruff check/format, mypy strict, pip check, Biome, TypeScript e Next build: aprovados. Compose config e Docker build backend: aprovados. Um aviso interno Starlette/AnyIO permanece.

## 17. Validação funcional e visual

API real com PostgreSQL temporário foi exercitada pelos testes do fluxo com fake, incluindo publicação e transferência. Não houve chamada real ao provedor externo. Build compilou as páginas novas e existentes. Imagem Docker final foi aplicada ao backend local: /health 200 e /professional/ai/config anônimo 401. Não havia navegador automatizado configurado; por isso inspeção visual de 1366/1024/768/375 px, smoke visual de Informativos/Notifications/Transferência/AuditLog, interação de teclado no navegador e capturas permanecem sem validação real. O build padrão repetido encontrou `EPERM` em `.next` no OneDrive; o build final passou em diretório temporário e este foi removido. Uma consulta redundante de Alembic current ao final demorou e foi interrompida; o current inicial confirmou 20260913_09 e o check posterior não detectou divergência.

## 18. Débitos e preparação para Dia 13

Sem AIGeneration persistida, quota/billing, idempotência de pedidos repetidos, histórico de falhas, retry técnico, auditoria clínica automática ou inspeção visual. A segurança clínica continua dependente da revisão profissional; o filtro de palavras não substitui avaliação. Antes de habilitar o provedor em ambiente real, definir política de consentimento, retenção e tratamento dos dados externos. Possível metodologia por Professional fica para trabalho futuro; não foi antecipado schema. O trabalho termina no Dia 12, sem commit ou push.