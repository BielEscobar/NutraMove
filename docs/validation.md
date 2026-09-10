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
