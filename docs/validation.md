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
