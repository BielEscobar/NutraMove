# Dia 15 — Relatório final da V1

Data: 15 de setembro de 2026. O código, os testes e os comandos desta etapa são a fonte deste relatório. Nenhum commit, push, merge, tag, release ou deploy público foi executado.

## 1. Resumo executivo

A V1 foi congelada, revisada e homologada localmente. A regressão final passou com 404 testes. Os módulos dos três perfis, autorização, segurança, migrations e stack de produção foram revalidados. A dívida visual autenticada dos Dias 10–12 foi coberta com contas e banco sintéticos em 112 combinações de rota, papel e viewport. Foram corrigidos dois defeitos de layout e uma instabilidade de teste na passagem da meia-noite. A documentação de entrega e operação foi concluída.

## 2. Estado inicial

Branch `develop`, HEAD `67ee4c0`, com o trabalho do Dia 14 ainda sem commit. As mudanças locais foram preservadas. Alembic estava em `20260913_10 (head)`. Não havia VPS, domínio, SSH ou credenciais de produção no ambiente.

## 3. Bugs encontrados

- A lista MASTER de Students permitia rolagem horizontal da página em 768 px quando a tabela excedia a área restante ao lado da navegação.
- A classe responsiva ativava colunas de grid na AppShell sem garantir `display:grid`; ao tornar a navegação lateral visível, links podiam se sobrepor no desktop.
- Um caso de teste definia “amanhã” como `date.today() + 1` e cruzou a meia-noite durante a suíte; no momento da validação, a data já era hoje.
- O `Caddyfile.prod` era válido, mas o formatador oficial apontava indentação não canônica.

## 4. Bugs corrigidos

A AppShell passa a usar grid explicitamente, mantém navegação superior até 768 px e usa uma coluna lateral a partir de 1024 px. A navegação recebeu regras de colunas explícitas para mobile, tablet e desktop. A repetição final não encontrou overflow ou sobreposição. O caso de data futura passou a usar margem de dois dias, sem mudar a regra da API. O Caddyfile foi formatado conforme o parser oficial.

## 5. MASTER — homologação

Login, dashboard, Professionals, Students, filtros, detalhe, estados, transferência, AuditLog, Informativos somente leitura, Notification própria e logout estão cobertos pela suíte completa. Criação, edição, ativação/desativação, aprovação/rejeição e empty/error states têm testes de API e componentes existentes. No navegador autenticado foram abertas dashboard, listas, detalhe, auditoria, informativos e inbox com dados fictícios.

## 6. Professional — homologação

Dashboard, carteira própria, busca e detalhe de Student, Diet, Workout, Assessment, Evolution, Hydration, Reevaluation, Information, Notification e IA desabilitada foram reexecutados pela regressão. O navegador autenticado abriu 12 rotas críticas, inclusive editores de Diet e Workout, nas quatro larguras.

## 7. Student — homologação

Cadastro, pendência, aprovação, login ACTIVE, dashboard, perfil, planos, evolução, hidratação, reavaliação, informativos, notificações e logout foram revalidados pela suíte. O navegador autenticado abriu nove rotas nas quatro larguras. O banco visual continha somente pessoas fictícias.

## 8. Diet

Criação manual, versões, edição, revisão otimista, duplicação, aprovação, arquivamento anterior, visibilidade exclusiva de versão aprovada ao Student e Notification após aprovação passaram na regressão. A geração fake mantém origem `AI_GENERATED` e estado `PENDING_REVIEW`.

## 9. Workout

Criação, dias/exercícios, versões, duplicação, edição, revisão otimista, aprovação, visibilidade ao Student e Notification foram reexecutados. IA fake segue o mesmo fluxo de revisão e nunca publica automaticamente.

## 10. Assessment e Evolution

Peso, altura, medidas, IMC derivado, histórico, correção, `edit_revision`, filtros e transferência passaram. IMC permanece apresentado como indicador derivado. O único teste instável de data futura foi corrigido e os dez casos parametrizados passaram antes da suíte final.

## 11. Hydration

Meta, atalhos 250/300/500 ml, valor customizado, timezone, total diário, histórico, gráfico e acesso por Student/Professional/MASTER continuam cobertos, inclusive limites de dia e DST.

## 12. Reevaluation

O fluxo PENDING → IN_REVIEW → COMPLETED, resposta visível ao Student, cancelamento, unicidade de solicitação aberta e bloqueio de transferência durante análise passaram.

## 13. Information

Rascunho, edição, publicação, arquivamento, audiência geral/individual, carteira e Notification transacional após publicação passaram.

## 14. Notifications

Inbox, contagem não lida, leitura individual/em lote, links tipados, ownership e eventos de Information, Diet, Workout e Reevaluation passaram. MASTER continua sem acesso a inbox alheia.

## 15. Transfer

Os testes confirmam A→B, perda imediata de acesso por A, ganho imediato por B sem novo login, preservação de histórico e planos e bloqueio de edição da autoria clínica antiga. Recurso fora da carteira retorna 404 e `IN_REVIEW` bloqueia a operação.

## 16. AuditLog

A transferência gera AuditLog com ator, Student e profissionais anterior/novo, sem senha, token ou conteúdo clínico. MASTER consulta; outros perfis não recebem acesso administrativo.

## 17. NutraMove AI

`AI_ENABLED=false` permanece o padrão. O fluxo manual funciona nessa condição. Os testes habilitam apenas provider fake e verificam Diet/Workout como `AI_GENERATED`, `PENDING_REVIEW`, invisíveis ao Student até aprovação, editáveis pelo Professional e notificadas somente após aprovação. Nenhum provider pago foi chamado.

## 18. RBAC e IDOR/BOLA

A matriz automatizada usa Professional A/B e Student A/B e cobre recursos filhos de Diet, Workout, Assessment, Evolution, Hydration, Reevaluation, Information e AI. Fora da carteira resulta em 404; papel inadequado, em 403; anônimo, em 401. MASTER não ganhou funções clínicas e Student não acessa APIs administrativas.

## 19. Rate limiting

Login, cadastro Student e IA passaram nos testes de janela, concorrência, 429 e `Retry-After`. Os limites permanecem 10/5 minutos, 5/hora e 10/hora, respectivamente.

## 20. Segurança

Foram revalidados sessão opaca, cookie HttpOnly/SameSite e Secure/`__Host-` em produção, Origin, CORS restrito, `no-store`, headers, docs off, health mínimo, segredos ausentes do frontend e ausência de porta pública para PostgreSQL/API/Next. Configuração real de borda continua dependente da VPS.

## 21. Visual

Chrome headless real, API real e PostgreSQL temporário abriram 28 rotas autenticadas: sete MASTER, doze Professional e nove Student. Cada rota foi repetida em 1366, 1024, 768 e 375 px, totalizando 112 verificações. Capturas de dashboard dos três perfis em desktop/mobile foram inspecionadas. A primeira rodada revelou os dois bugs de layout; somente a rodada posterior às correções foi aceita.

## 22. Mobile

Em 375 px, menu, cabeçalho, cards, botões, formulários e páginas críticas permaneceram utilizáveis e sem overflow horizontal. Tabelas continuam com contêiner de rolagem próprio quando necessário. A inspeção não substitui teste em aparelhos físicos.

## 23. Acessibilidade

A revisão combinou testes existentes, inspeção estática e navegador para headings, labels, foco, dialogs nativos, alert/status, texto de estado, alvos de toque e alternativas textuais dos gráficos. Não foi feita auditoria WCAG nem medição formal de contraste.

## 24. Console e Network

Não houve `Runtime.exceptionThrown`, erro de hidratação React, loop infinito, CORS ou mixed content no ambiente HTTP local. O CDP registrou apenas `net::ERR_ABORTED` causado pela navegação forçada entre páginas durante a matriz; esses abortos eram esperados e não representam falha de API. Testes de integração verificam status e `no-store`. Nenhuma chave, senha ou token apareceu em resposta de aplicação examinada. HTTPS real não estava disponível.

## 25. Produção Docker

`infra/compose.prod.yaml` mantém somente 80/443 publicadas, redes `edge`/`data`, PostgreSQL interno, API/Next internos, volumes nomeados, healthchecks, restart e rotação de logs. O backend Docker compilou na rodada final; o frontend foi reconstruído após remover os artefatos temporários do navegador do contexto.

## 26. Caddy

O parser oficial validou os dois hosts fictícios, proxies app→frontend e api→backend, compressão, HSTS moderado e redirect automático HTTP→HTTPS. Não há CSP concorrente. Certificado real não foi solicitado.

## 27. Trusted proxy

Caddy permanece em `172.30.46.10` dentro de `172.30.46.0/24`; Uvicorn confia somente nesse endereço e a API não publica porta. A subnet e o IP observado precisam ser confirmados na VPS. Qualquer Cloudflare futuro exige nova política de origem/proxy.

## 28. PostgreSQL

PostgreSQL 17 permanece isolado na rede interna e em volume nomeado. A persistência após recriação de contêiner foi comprovada no Dia 14 com dado sintético e o desenho não mudou no Dia 15.

## 29. Migrations

`alembic heads`, `current` e `check` confirmaram `20260913_10 (head)` e nenhuma operação nova. Não houve mudança de schema nem migration no Dia 15.

## 30. Backup

O script usa dump custom, arquivo temporário, verificação de catálogo, SHA-256 e retenção provisória. A sintaxe Bash foi revalidada em Linux. O fluxo completo com banco sintético foi comprovado no Dia 14; agendamento e cópia externa dependem da VPS.

## 31. Restore

Restore permanece restrito a banco temporário, com checksum, `--exit-on-error`, Alembic e dado conhecido. O teste do Dia 14 restaurou `20260913_10` e o registro sintético, depois removeu banco e dump. Nenhum restore foi feito sobre banco operacional.

## 32. Testes

Rodada final: **404 passaram, nenhum skip**, em 10m09s, com um `DeprecationWarning` interno Starlette/AnyIO conhecido. A primeira rodada, iniciada antes da meia-noite e concluída depois, teve 403 passagens e a falha instável descrita; após a correção, o caso isolado passou 10/10 e a suíte completa ficou verde.

## 33. Qualidade backend

Ruff check/format, mypy strict e `pip check` foram executados após remover scripts temporários. Os resultados finais constam também em [validation.md](validation.md).

## 34. Qualidade frontend

Biome, TypeScript, Next production build e `npm audit --omit=dev --audit-level=high` foram executados após a limpeza dos artefatos de homologação. Os resultados finais constam em [validation.md](validation.md).

## 35. Docker

Compose prod `config --quiet`, builds backend/frontend, Caddy validate e inspeção do desenho de portas/redes foram repetidos com valores sintéticos. Nenhuma imagem foi enviada a registry.

## 36. Documentação

Foram criados [client-handover.md](client-handover.md), [operator-guide.md](operator-guide.md), [release-checklist.md](release-checklist.md), [CHANGELOG.md](../CHANGELOG.md) e este relatório. O README foi condensado e aponta arquitetura, validação, segurança, privacidade, deploy, backup/restore e entrega.

## 37. Git cleanliness

Foram revisados `.env`, chaves, certificados, dumps, backups, logs, screenshots, caches, `.next`, venv, tokens e senhas. Dados, credenciais, perfil Chrome e schema da homologação eram temporários e foram removidos. Arquivos locais ignorados existentes não foram adicionados. `git diff --check` passou.

## 38. Arquivo estranho

O arquivo não rastreado `ecurity and prepare production\uf022`, citado no Dia 14, tinha 16.465 bytes de ajuda do pager `less`, com caracteres de controle/backspace. Era um artefato acidental de terminal, não foi executado e foi removido após validar nome, caminho e tamanho.

## 39. Débitos

Permanecem teste E2E persistente, auditoria WCAG, teste de segurança independente, política jurídica/LGPD e IA, recuperação de senha/MFA, monitoramento operacional, RPO/RTO e retenção formal. São decisões ou evoluções posteriores; nenhuma feature V2 foi iniciada.

## 40. Pendências exclusivas de VPS/domínio

SSH/firewall, conflito de subnet, DNS, certificado e renovação, HSTS/redirect público, cookies e Origin/CORS em HTTPS, IP real no proxy, recursos da máquina, restart/reboot, secrets reais, registry/digests, cron, backup externo, restore da cópia externa, smoke autenticado público e observação inicial.

## 41. CODE READY

**SIM, localmente.** Testes, lint, tipos, builds, migrations e homologação local estão aprovados. A árvore contém mudanças ainda sem commit, por instrução.

## 42. INFRA READY

**PREPARADA E VALIDADA LOCALMENTE.** Compose, imagens, Caddy, persistência e restore sintético estão prontos para aplicação pelo runbook. A operação na VPS ainda precisa ser executada.

## 43. PUBLIC DEPLOY READY

**NÃO VALIDADO.** Não havia VPS, domínio, DNS, TLS ou credenciais. Isso limita a evidência operacional e não indica falha do código.

## 44. Comandos sugeridos de merge e tag

Somente após revisão humana do diff, aprovação e escolha do fluxo de integração:

```bash
git add <arquivos-aprovados>
git commit -m "Prepare NutraMove V1 release"
git switch main
git merge --ff-only develop
git tag -a v1.0.0 -m "NutraMove V1.0.0"
git push origin main
git push origin v1.0.0
```

Se `main` não permitir fast-forward, use pull request/revisão conforme a política do repositório. Não force histórico nem inclua `.env`, dumps, screenshots ou caches.

## 45. Checklist para deploy

Use [release-checklist.md](release-checklist.md). Antes de abrir tráfego: commit/tag aprovados, env 0600, segredos fortes, DNS, firewall/SSH, backup e restore verificados, imagens/digests registrados, migration única, containers healthy, TLS, smoke dos três papéis, transferência/AuditLog, segurança, visual e remoção de contas fictícias.

## 46. Checklist pós-deploy

Nas primeiras 24 horas: acompanhar health/ps, 5xx/429, logs sem dados sensíveis, certificado, CPU/memória/disco, execução e cópia do backup, login/logout, páginas críticas, notifications, reinício seguro e contatos de incidente. Registrar versão, digests, horário, operador, resultado e eventual rollback.

## 47. Conclusão da V1

A implementação da V1 termina neste estado de código preparado e homologado localmente. A próxima ação é revisão da árvore, commit/release autorizados e execução manual do runbook no ambiente público. O ciclo não avançou para V2.
