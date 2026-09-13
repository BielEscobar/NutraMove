# Verificação da fundação

Verificações executadas em 8 de setembro de 2026, no Windows 11, com Node.js
24.20.0, npm 11.19.0, Python 3.13.7, Docker 29.7.2 e Compose 5.5.1.

| Verificação | Resultado |
| --- | --- |
| pytest | 10 testes passaram; um aviso interno de dependência. |
| Ruff lint e formatação | Aprovados. |
| mypy strict | Nenhum erro em 21 arquivos Python. |
| pip check | Nenhuma dependência incompatível. |
| Biome | Lint e formatação aprovados. |
| TypeScript | Typecheck aprovado. |
| Next.js | Build de produção aprovado; página inicial estática. |
| npm ls --depth=0 | Dependências diretas resolvidas. |
| Docker Compose config --quiet | Configuração válida. |
| Docker build | Imagem do backend construída. |
| Docker Compose up --wait | Backend e PostgreSQL saudáveis. |
| HTTP GET /health no contêiner | Resposta com status ok. |
| Alembic upgrade head e check | Executados; nenhuma operação nova detectada. |
| SQLAlchemy SELECT 1 em PostgreSQL | Conexão confirmada. |
| Git | Arquivos locais .env ignorados; nenhuma alteração commitada. |

## Ajustes e pontos de atenção

- O sandbox bloqueou acesso aos registros de pacotes e ao Docker. As operações
  necessárias foram executadas com permissão fora do sandbox.
- O scaffold trouxe ESLint 9 sem suporte. ESLint 10 falhou com os plugins React
  distribuídos por eslint-config-next. O projeto usa Biome 2.5.12 como linter e
  formatador; sua configuração foi migrada para a sintaxe atual.
- O cliente de testes usa httpx2, conforme a recomendação atual do
  [Starlette](https://www.starlette.io/testclient/).
- Resta um DeprecationWarning originado em starlette/testclient.py, pela referência
  interna a anyio.abc.BlockingPortal. O código do projeto não utiliza esse alias.
  O aviso não foi ocultado e não impede os testes; acompanhar atualização upstream.
- O pip emitiu seu aviso padrão sobre instalação como root durante a construção da
  imagem. A aplicação dentro do contêiner executa como appuser.
- A primeira consulta SQL de verificação falhou por interpretação de aspas no
  PowerShell. A repetição via entrada padrão confirmou a conexão.
- Foram criados backend/.env, infra/.env e frontend/.env.local para validação local.
  A senha do PostgreSQL foi gerada aleatoriamente, sem exibi-la ou versioná-la.
- As versões Python diretas estão fixadas; as transitivas não têm lockfile nesta
  fundação. O frontend possui package-lock.json.
- Não há testes de interface ou de negócio: o frontend é apenas uma página estática.
  Os testes Python cobrem health, CORS, configuração e respostas de erro.

## Autenticação — 10 de setembro de 2026

- 40 testes passaram usando PostgreSQL em schema isolado; nenhum teste foi pulado.
- Upgrade, downgrade e novo upgrade da migration 20260910_01 foram verificados
  no schema temporário. Alembic check não identificou diferenças.
- A migration foi aplicada no banco local; a API atualizada e PostgreSQL estão saudáveis.
- HTTP real no contêiner: /health retorna 200; /auth/me sem sessão retorna 401.
- Ruff lint e formatação: aprovados.
- mypy strict: nenhum erro em 35 arquivos.
- pip check: nenhuma incompatibilidade.
- Biome: lint/formatação aprovados em 14 arquivos.
- TypeScript: aprovado.
- Build Next.js de produção: aprovado, com /login e /account.
- Build Docker do backend: aprovado.
- Fonte Inter incluída localmente com licença OFL; nenhuma dependência npm foi adicionada.
- Dependências Python adicionadas: pwdlib[argon2] 0.3.1 e email-validator 2.3.0.

O aviso interno Starlette/AnyIO permanece visível. Houve bloqueios de acesso à rede
no sandbox, resolvidos pela execução autorizada. O cache do pytest apresentou
permissão negada; a verificação final usou -p no:cacheprovider, sem desabilitar testes.
O Biome apontou uma dependência desnecessária no effect de tentar novamente;
o fluxo foi simplificado e a verificação passou.

Não foi executada automação de navegador. Não há usuário padrão ou seed de
credenciais. A criação do primeiro MASTER é interativa.
Nenhum commit foi criado.

Veja [decisões de autenticação](authentication.md) e
[inventário dos arquivos](authentication-files.md).


## Validação final — MASTER (10/09/2026)

93 testes PostgreSQL aprovados, nenhum pulado. Ruff lint/formatação, mypy strict
(42 arquivos), pip check, Biome (27 arquivos), TypeScript e build Next.js aprovados.
Build Docker e Compose config --quiet aprovados. Migration 20260910_02 aplicada
no banco local; Alembic current confirmou head e check não encontrou divergências.
Upgrade/downgrade também foram testados em schemas isolados. Contêineres saudáveis.
Smoke HTTP: /health 200, /master/professionals anônimo 401.
Não foi executada validação visual ou automação de navegador.
Avisos: Starlette/AnyIO deprecated alias; pip como root durante construção da imagem
(a execução do backend usa appuser); Git informou conversão LF/CRLF.
O aviso de lint frontend foi corrigido. Nenhuma dependência adicionada.


## Dia 4 — Student (10/09/2026)

166 testes PostgreSQL passaram, nenhum pulado. Ruff check e format --check,
mypy strict (49 arquivos), pip check, Biome (42 arquivos), TypeScript e build
Next.js aprovados. Compose config --quiet e build Docker aprovados.
Migration 20260910_03 aplicada localmente; Alembic current confirmou head e check
sem divergências. Upgrade/downgrade/check também passaram em schemas isolados.
Contêineres saudáveis; /health 200 e /students/me anônimo 401.

Verificação pontual com Chrome headless/CDP, sem dependência adicionada: onboarding
em 390 px, aluno pendente, aprovação/edição/desativação/reativação pelo profissional,
novo login de aluno ativo e listagem MASTER. Sem exceções JavaScript não tratadas.
Capturas mobile e desktop inspecionadas. Dados sintéticos em schema temporário.
Não há suíte E2E persistente no repositório.

Falhas corrigidas durante a implementação: formatação/linhas longas de Python,
tipos de índices heterogêneos em testes, nome de prop role confundido pelo lint
com ARIA (renomeado allowedRole). Na automação de navegador, uma espera por
hidratação React corrigiu o preenchimento inicial. O helper teve demora de leitura
local de módulos Python antes de iniciar; isso não foi falha da aplicação.
O aviso interno Starlette/AnyIO permanece visível. Git também informa LF/CRLF.


## Dia 5 — Dashboards (10/09/2026)

185 testes passaram, nenhum pulado. Ruff check/format aprovados; mypy strict em
53 arquivos sem erros; pip check sem incompatibilidades. Biome em 48 arquivos,
TypeScript e build Next.js aprovados. Docker build e Compose config --quiet
aprovados. Backend atualizado e saudável; Alembic current 20260910_03 (head) e
check sem divergências. Nenhuma migration nova.

Chrome/CDP com API real e schema isolado: os três dashboards em 1366, 1024, 768 e
375 px, sem overflow horizontal; login por role, anônimo, acesso de papel errado,
navegação, logout, erro de API com retry e estados pendente/rejeitado/carteira vazia
aprovados. Áreas de toque da navegação/logout verificadas; capturas representativas
inspecionadas. Nenhuma exceção JavaScript não tratada. Não foi instalada suíte E2E.

Aviso conhecido Starlette/AnyIO permanece visível; avisos LF/CRLF do Git também.
O teste de erro usa bloqueio temporário de rede no navegador e recupera acesso
real antes do retry. Não há mock permanente. Detalhes em dashboards.md.

## Dia 6 — Dietas (10 de setembro de 2026)

- pytest: 217 passaram, nenhum pulado; 32 testes específicos de dieta.
- Ruff check e format --check: aprovados; mypy: 61 arquivos sem erros; pip check aprovado.
- Biome: 65 arquivos aprovado; TypeScript e build Next.js aprovados.
- Docker build aprovado. Migration 04 validada com upgrade/downgrade/check nas fixtures.
- Chrome/API real: criação, publicação, duplicação, edição, republicação, histórico,
  leitura Student e MASTER passaram. Editor e leitor em 1366/1024/768/375 sem overflow
  horizontal nem exceções JS não tratadas; capturas representativas inspecionadas.
- Corrigidos conflito de nome do tipo datetime.time e ajustes de lint durante implementação.
  Exceção de chave por posição no leitor está justificada e limitada a snapshots de leitura.
- Permanece apenas o aviso de depreciação interno Starlette/AnyIO conhecido.

Dados de navegador sintéticos foram isolados em schema temporário. Não foi instalada
suíte E2E nem adicionada dependência. Consulte diets.md para limites e arquivos.

Validação local final: Compose config aprovado; Docker backend e PostgreSQL saudáveis;
Alembic current = 20260910_04 (head), check sem divergências. A verificação auxiliar
teve um erro de tipo ao passar PostgresDsn diretamente para create_engine; corrigida
para str apenas no comando de inspeção, sem alteração no código da aplicação.

## Dia 7 — Workout (10 de setembro de 2026)

- pytest completo: 260 passaram, nenhum pulado; 43 específicos de treino.
- Ruff check e format --check aprovados (68 arquivos); mypy strict: 68 arquivos sem erros.
- pip check aprovado; Biome: 83 arquivos aprovado; TypeScript e build Next.js aprovados.
- Compose config --quiet e build Docker backend aprovados.
- Migration 20260910_05 revisada; upgrade/downgrade/check passaram nos schemas de teste.
- Nenhuma dependência nova; nenhum teste pulado. Aviso interno Starlette/AnyIO permanece.

A conexão de inspeção por localhost ficou pendente; foi encerrada e substituída por
127.0.0.1 com timeout na execução dos testes e geração da migration, sem alterar .env.
Ajustes iniciais de formatação foram corrigidos. O teste de navegador precisou aguardar
Chrome iniciar e corrigir seletores de texto/link; isso não exigiu mudança na aplicação.

Validação final do Dia 7: migration local 20260910_05 (head), Alembic check sem divergências,
backend e PostgreSQL saudáveis. Chrome headless com API real validou login, abertura do
aluno, criação de divisão/exercício, salvar/publicar, leitura Student, duplicação/edição,
histórico intacto antes de republicar e entrega da versão 2 ao aluno. MASTER somente leitura.
Editor e leitor foram testados em 1366, 1024, 768 e 375 px sem overflow horizontal ou
exceções JavaScript não tratadas. Capturas representativas dos quatro tamanhos foram
inspecionadas visualmente, incluindo instruções abertas em 375 px. Não há suíte E2E
persistente; os testes usaram schema e contas temporários, removidos ao terminar.

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

## Validação final do Dia 9 — Hidratação e reavaliações

- Estado inicial: branch develop, alterações locais do Dia 8 preservadas;
  Alembic HEAD e banco local confirmados em 20260911_06 antes da edição.
- pytest completo: **344 passaram**, nenhum pulado; **51 testes novos**.
  Os testes usam PostgreSQL e verificam upgrade/downgrade/upgrade/check em schemas isolados.
- Testes específicos de hidratação/reavaliações/dashboard: 70 passaram na primeira rodada.
- Ruff check e format --check aprovados; mypy strict: **89 arquivos**, sem erros.
- pip check aprovado. Nenhuma dependência nova.
- Biome/lint: **113 arquivos**, aprovado. TypeScript e build Next.js aprovados.
- Compose config --quiet e Docker build aprovados.
- Migration 20260911_07 revisada, aplicada localmente e backend atualizado.
  Alembic current: 20260911_07 (head); check sem novas operações.

### Verificações de dados e autorização

Inteiro de água (incluindo rejeição de boolean/string/fração), horários aware,
tolerância de futuro, data de negócio America/Sao_Paulo, fronteiras exatas do dia,
histórico 1/7/30 dias e dia de 23 horas em fuso com DST. Agregações SQL, meta em litros
convertida para ml, meta ausente/zero, percentual acima de 100 e restante não negativo.

Reavaliações: cadastro ACTIVE/vínculo ativo, campos extras, categorias, motivo/resposta,
um pedido aberto, workflow, autores/timestamps, cancelamento, filtros e paginação,
contagens, Origin, MASTER somente leitura e Student/Professional isolados.
Teste de concorrência com duas conexões reais retornou 201/409 e somente um registro.
Índice parcial também foi exercitado por inserção direta conflitante.

### Chrome e API real

Schema test_browser_day9_* com contas sintéticas, API temporária 8001 e frontend 3001.
Perfil Chrome headless próprio, sem utilizar sessão pessoal do navegador.

- Student: login, hidratação, 250 + 500 = 750 ml, meta 2,5 L, 30%, histórico e gráfico.
- Professional: leitura do consumo da carteira e alteração da meta para 3 L pelo
  PATCH existente; percentual passou a 25% sem alterar o consumo.
- Student solicita revisão de treino; dashboard Professional indica pendência;
  inicia análise, responde e conclui; Student consulta a resposta/conclusão.
- Outro Professional recebeu erro de registro não encontrado para hidratação e pedido.
  MASTER consultou sem campo de resposta/ações de workflow.
- Erro de rede de histórico e retry verificados com bloqueio transitório no Chrome.
- Duplicidade apresentou a mensagem amigável; cancelamento pendente exigiu confirmação.
- Dashboard de água e logout conferidos. Nenhuma exceção JavaScript não tratada.

Hidratação, formulário de solicitação, lista Professional e detalhe em
1366, 1024, 768 e 375 px, sem overflow horizontal. Capturas dos quatro tamanhos
inspecionadas; capturas adicionais de atalhos, horário, formulário e gráfico mobile.
Gráfico contém alternativa textual; rótulos, estados e progresso não dependem só de cor.

API/frontend/Chrome temporários encerrados e schema removido. Contas demo e dados reais
preservados. Não foi adicionada suíte E2E persistente.

### Problemas encontrados

Imports/formatação da migration gerada e a importação da fixture compartilhada foram
ajustados após lint. O lint final também normalizou a formatação do AppShell após a
reordenação dos links. Um comando npm auxiliar foi iniciado na raiz (sem package.json);
foi repetido corretamente em frontend/. Uma substituição de texto perdeu acentuação
na passagem pelo stdin do Windows; o documento foi corrigido em UTF-8.

Acesso inicial ao Docker e inspeção dos processos temporários exigiram execução fora
do sandbox. As operações autorizadas foram concluídas. Permanece somente o aviso interno
Starlette/AnyIO sobre BlockingPortal, sem ocultação e sem uso desse alias pelo projeto.

Consulte [hydration.md](hydration.md), [reevaluations.md](reevaluations.md) e
[dia9-relatorio.md](dia9-relatorio.md) para arquivos, decisões e limites.

Checagem de encerramento: typecheck e build final aprovados após encerrar o dev de teste;
backend e PostgreSQL locais saudáveis; /health 200; novos endpoints anônimos retornam 401.
A chamada auxiliar inicial do smoke HTTP teve erro de aspas no PowerShell, corrigido
com script via stdin, sem alteração na aplicação. git diff --check aprovado.
Arquivos temporários, credenciais sintéticas e perfil de navegador removidos.

## Verificação do Dia 10 — informativos e notificações

Backend: 373 testes passaram, nenhum pulado; Ruff check e format --check aprovados; mypy strict aprovado em 102 arquivos; pip check sem incompatibilidades. Frontend: Biome aprovado em 127 arquivos, TypeScript e build Next.js aprovados. Compose config --quiet aprovado. Alembic local: 20260912_08 (head), check sem operações novas; upgrade/downgrade/upgrade em schemas de testes. Docker build aprovado. Não houve validação de navegador ou inspeção visual nesta execução. Permanece um DeprecationWarning interno Starlette/AnyIO.
