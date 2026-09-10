# Gestão de profissionais — MASTER

Implementada em 10 de setembro de 2026. Esta etapa não inclui Student ou onboarding.

## Comportamento e decisões

Somente MASTER autenticado pode acessar os endpoints administrativos. A role é
consultada no banco em cada requisição; os formulários não definem permissões.
Professional possui UUID, user_id obrigatório e único, especialidade opcional e
timestamps. Nome, e-mail, hash da senha e status pertencem exclusivamente a User.
A FK usa RESTRICT para preservar o vínculo.

A criação sempre cria um novo User com role PROFESSIONAL e seu Professional na
mesma transação. Não vincula contas existentes. O MASTER define a senha inicial
(12 a 128 caracteres); não há convite, envio de e-mail ou alteração de senha nesta
etapa. Somente o hash Argon2 é persistido.

A edição permite nome, e-mail e especialidade (texto livre até 120 caracteres).
E-mail duplicado retorna 409. Campos adicionais são rejeitados. Desativar mantém
os registros e revoga todas as sessões na mesma transação. Reativar exige novo
login. Login e alteração de status bloqueiam a mesma linha User durante a
transação para serializar criação e revogação de sessões.

## API

Todos os caminhos abaixo começam com /master/professionals.

| Método | Caminho | Finalidade |
| --- | --- | --- |
| GET | / | Listar e buscar |
| GET | /summary | Totais reais de ativos e inativos |
| POST | / | Criar usuário e profissional |
| GET | /{id} | Consultar cadastro |
| PATCH | /{id} | Editar cadastro |
| POST | /{id}/activate | Ativar ou reativar |
| POST | /{id}/deactivate | Desativar e revogar sessões |

Nos caminhos da coleção, use o prefixo sem barra final.
Busca q por nome, e-mail ou especialidade, sem diferenciar maiúsculas; caracteres
% e _ são literais. Filtro is_active opcional. Paginação page começa em 1;
page_size padrão 20, máximo 100. Ordenação por nome e UUID.
Respostas não incluem senha, hash ou token. Mutação exige Origin confiável.
CORS foi ampliado somente com PATCH.

## Arquivos e organização

- backend/app/models/professional.py: mapeamento SQLAlchemy.
- backend/app/schemas/professional.py: validação e respostas explícitas.
- backend/app/repositories/professionals.py: consultas, busca e bloqueios.
- backend/app/services/professionals.py: transações e regras administrativas.
- backend/app/api/professionals.py: rotas protegidas.
- backend/alembic/versions/20260910_02_professionals.py: nova tabela, dependente
  de 20260910_01. A migration anterior foi preservada.
- backend/tests/test_professionals.py: testes de gestão e autorização.
- backend/tests/conftest.py: fixtures PostgreSQL compartilhadas com autenticação.
- frontend/src/app/master/: layout, visão geral, lista, criação, detalhe e edição.
- frontend/src/components/master/: formulário, detalhe, editor e estados comuns.
- frontend/src/lib/professionals.ts: contratos TypeScript.
- frontend/src/lib/use-master-resource.ts: carregamento, cancelamento e erros.

Integrações modificadas: main.py e models/__init__.py registram o módulo;
repositories/auth_sessions.py revoga sessões; repositories/users.py e
services/auth.py acrescentam o bloqueio no login. Os testes anteriores foram
preservados com fixtures compartilhadas. Login direciona MASTER para /master;
a conta oferece acesso à administração. Cliente HTTP e CSS receberam mensagens
e estilos comuns. Nenhuma dependência foi adicionada.

## Validação e limites

93 testes backend passaram, sem pulos, usando PostgreSQL real e schemas isolados.
Cobrem permissões de todas as roles, campos injetados, atomicidade, duplicidade,
busca, paginação, constraints, CSRF e revogação de múltiplas sessões.
Upgrade, downgrade e Alembic check foram verificados nos schemas de teste.
Ruff, mypy strict (42 arquivos) e pip check passaram.
Frontend: lint Biome, typecheck e build Next.js passaram.

Permanece um DeprecationWarning interno do Starlette relacionado a
anyio.abc.BlockingPortal. O primeiro lint frontend apontou uso de optional chaining,
corrigido antes da validação final. Não há suíte automatizada de navegador;
build e testes da API não comprovam validação visual ou fluxo completo no navegador.

Continuam pendentes rate limiting, recuperação/troca de senha, infraestrutura
de produção e testes de navegador. Nenhuma conta foi criada automaticamente,
nenhum commit foi realizado e Student não foi implementado.


Migration 20260910_02 aplicada ao banco local; Alembic check sem divergências.
Build Docker aprovado e contêineres saudáveis. Smoke: /health 200 e gestão anônima 401.
