# Inventário técnico de privacidade — LGPD

Documento de engenharia para discussão com controlador, encarregado/DPO e assessoria. Não define base legal nem prazo de retenção por conta própria. A [LGPD compilada](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) e as [perguntas frequentes da ANPD](https://www.gov.br/anpd/pt-br/acesso-a-informacao/perguntas-frequentes/perguntas-frequentes) são referências para as decisões jurídicas. Dados relativos à saúde podem ser sensíveis; o tratamento deve ser avaliado com especial cuidado.

## Categorias e finalidade técnica

| Domínio | Categorias de dados | Finalidade no sistema | Acesso técnico |
| --- | --- | --- | --- |
| User/AuthSession | Nome, e-mail, hash de senha, hash de token, papel, status e expiração | Identidade, sessão e autorização | Próprio User; MASTER em administração prevista; serviços de autenticação |
| Professional | Dados cadastrais/profissionais, vínculo a User | Carteira e administração | Próprio Professional e MASTER |
| Student | Cadastro, objetivo, rotina, peso/altura, preferências/restrições, contato | Acompanhamento | Próprio Student, Professional da carteira atual e MASTER conforme telas |
| Diet/Workout e versões | Conteúdo de planos, autoria, status e datas | Planejamento e histórico | Student só versão aprovada; Professional da carteira atual; MASTER leitura |
| Assessment/Measurement | Peso, altura, medidas, notas e histórico | Evolução | Student próprio; Professional da carteira atual; MASTER leitura |
| WaterRecord | Consumo e horário | Hidratação | Student próprio; Professional da carteira atual; MASTER leitura |
| ReevaluationRequest | Categoria, motivo, resposta, responsáveis e datas | Solicitação e atendimento | Student próprio; Professional da carteira atual; MASTER leitura |
| Information | Texto, audiência e autoria | Informativos | Publicados à audiência Student; Professional autor/carteira; MASTER leitura |
| Notification | Tipo, mensagem curta, recurso, leitura | Inbox interna | User destinatário somente |
| AuditLog | Ator, Student, origem/destino, motivo e data | Rastreabilidade de transferência | MASTER |
| RateLimitWindow | HMAC de endereço ou User, janela e contagem | Reduzir abuso técnico | Backend; sem endpoint público |
| NutraMove AI | Contexto mínimo, orientações e saída proposta | Rascunho assistido | Professional da carteira; provedor externo somente quando habilitado |

Não incluir dados reais em documentação/testes. O backend não registra prompt, plano, motivo de reavaliação, medidas, cookies ou resposta bruta do provedor em logs de aplicação. A política do proxy e backups deve ser revista separadamente.

## Acesso, transferência e IA

O vínculo atual `Student.professional_id` define a carteira. Após transferência, novo Professional vê histórico clínico necessário à continuidade, mas não altera versões/avaliações atribuídas ao anterior. Informativos antigos deixam de aparecer ao Student conforme regra atual; Notification permanece do User. AuditLog documenta o ato da transferência. A política clínica de acesso histórico precisa de validação com o controlador antes de produção.

IA é opcional e `AI_ENABLED=false` por padrão. Se habilitada, podem sair do sistema: objetivo/detalhe, atividade, experiência/frequência/horário de treino ou horários, preferências e restrições alimentares, orientações livres do Professional e, se selecionados, objetivo do plano aprovado e data/peso da avaliação recente. Não se enviam nome, e-mail, telefone, UUID, senha, token, AuditLog, notificações ou perfil inteiro. O conteúdo livre pode conter dados pessoais ou sensíveis mesmo sem campos de identificação. É preciso definir e registrar finalidade, hipótese legal adequada, transparência ao titular, relação com o provedor/operador, localização/transferência internacional, retenção e canal para exercício de direitos antes da ativação externa. Não criar caixa de consentimento fictícia para substituir essa definição. Consulte [guia da ANPD para agentes de tratamento](https://www.gov.br/anpd/pt-br/assuntos/noticias/nova-versao-do-guia-dos-agentes-de-tratamento) e [regras sobre transferência internacional](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024).

## Retenção e direitos

Hoje o projeto não implementa exclusão/anonimização geral. Não aplicar DELETE CASCADE que destrua históricos, autorias ou auditoria. O controlador deve definir prazos por categoria e fundamento, fluxo de encerramento de conta, correção, acesso, portabilidade, bloqueio/anonimização/exclusão quando cabível, retenção legal/profissional e tratamento de backups. Direitos do titular exigem análise contextual; eliminação não significa apagar indiscriminadamente toda evidência. A [ANPD explica esses direitos](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares).

`RateLimitWindow` mantém apenas HMAC e contagem; registros sem atualização por mais de dois dias são removidos oportunisticamente quando há tráfego em endpoints limitados. Sem tráfego, a limpeza não ocorre automaticamente: definir tarefa operacional de limpeza/retention no Dia 14. Rotação de `RATE_LIMIT_SECRET` invalida chaves antigas, mas não as apaga; planejar limpeza.

## Backup, segurança e incidentes

No Dia 14 definir backup PostgreSQL criptografado, transporte seguro, volume persistente, acesso mínimo, retenção, restore test periódico, exclusão segura e controle de chaves/segredos. O [guia de segurança da ANPD](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-publica-guia-de-seguranca-para-agentes-de-tratamento-de-pequeno-porte) recomenda medidas técnicas e administrativas, incluindo controle de acesso e cópias de segurança. Também definir canal e procedimento de incidente, responsável e comunicação conforme avaliação aplicável. Não há deploy de produção nesta etapa.