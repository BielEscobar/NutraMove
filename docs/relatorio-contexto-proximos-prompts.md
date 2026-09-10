# NUTRAMOVE — Relatório de contexto para análise e próximos prompts

Data: 10 de setembro de 2026.

Este documento é autocontido: pode ser enviado a outro chat para analisar o projeto e
formular os próximos prompts. Descreve o código disponível, as verificações já
executadas e o trabalho pendente. Sugestões futuras não equivalem a funcionalidades
implementadas nem autorizam execução automática.

## 1. Resumo do estado real

O NUTRAMOVE possui a fundação técnica e a autenticação implementadas.
Ainda não possui o módulo administrativo MASTER de gestão de profissionais.

Existe User com roles MASTER, PROFESSIONAL e STUDENT. A existência dessas roles
não significa que existam as entidades Professional e Student, seus CRUDs ou dashboards.

A próxima etapa funcional solicitada anteriormente é MASTER + gestão de profissionais.
Essa etapa foi interrompida quando se constatou que a autenticação presumida pelo
pedido não existia. Após autorização do usuário, implementou-se primeiro essa base.
O desenvolvimento parou novamente ao finalizar a autenticação.

## 2. Contexto do desenvolvedor e regras de trabalho

O responsável pelo projeto está aprendendo Python e utiliza o NUTRAMOVE como
experiência prática e portfólio.

Os próximos prompts devem preservar estas regras:

- Código simples, legível, tipado e organizado; explicar a complexidade relevante.
- Não recriar a fundação nem substituir a autenticação existente.
- Não realizar grandes refatorações sem necessidade e justificativa.
- Implementar somente o escopo solicitado; não avançar automaticamente de etapa.
- Avaliar a necessidade antes de adicionar dependências.
- Usar APIs reais e suportadas, sem inventar bibliotecas.
- Validar toda autorização no backend; não confiar em role ou identificadores
  enviados pelo frontend para decidir permissões.
- Não armazenar senhas em texto puro nem colocar secrets no Git.
- Manter frontend e backend desacoplados.
- Utilizar PostgreSQL, SQLAlchemy 2.0 e migrations Alembic.
- Executar testes, lint, typecheck e build quando aplicável; comunicar falhas.
- Explicar arquivos alterados, decisões e pontos de atenção.
- Não criar commits automaticamente.
- Não implementar Student ou IA sem autorização específica.

## 3. Repositório e ambiente

| Item | Estado |
| --- | --- |
| Repositório informado | BielEscobar/NutraMove |
| Diretório local | C:\Users\BielE\OneDrive\Desktop\NutraMove\NutraMove |
| Branch de desenvolvimento | develop |
| Branch reservada para produção | main |
| Último commit local consultado | 86a0f9c — Primeiro Comit (Dia 01 e 02) |
| Alterações de autenticação | Presentes no diretório de trabalho, ainda sem commit |
| Sistema usado nas verificações anteriores | Windows 11, PowerShell |
| Node.js / npm verificados na fundação | 24.20.0 / 11.19.0 |
| Python verificado na fundação | 3.13.7 |
| Docker / Compose verificados na fundação | 29.7.2 / 5.5.1 |

Apesar do nome do commit mencionar dois dias, seu conteúdo original não incluía
autenticação. O próximo agente deve inspecionar arquivos e Git, sem inferir
funcionalidades pelo nome do commit.

O relatório foi preparado por leitura do código, documentação e estado do Git.
Testes e serviços não foram executados novamente apenas para gerar este documento.
Os resultados de execução abaixo correspondem à implementação anterior desta sessão.

## 4. Stack disponível

Frontend:

- Next.js 16.3.4 e React 19.2.8.
- TypeScript, Tailwind CSS, shadcn/ui e Lucide.
- Biome 2.5.12 para lint e formatação.
- Inter local, servida com next/font/local e licença OFL incluída.
- package-lock.json para instalação com npm ci.
- Recharts faz parte da stack oficial prevista, mas ainda não está instalado.

Backend — versões diretas fixadas em requirements.txt:

- FastAPI 0.141.1.
- Uvicorn 0.52.4.
- SQLAlchemy 2.0.52.
- Psycopg com binários 3.3.5.
- Pydantic 2.13.5.
- pydantic-settings 2.15.0.
- Alembic 1.19.2.
- pwdlib[argon2] 0.3.1.
- email-validator 2.3.0.

Qualidade backend: pytest, Ruff, mypy strict e httpx2 para o TestClient atual.

Infraestrutura: PostgreSQL 17 e backend no Docker Compose local.
Hostinger VPS permanece destino previsto, sem deploy implementado.

## 5. Arquitetura e pastas

```text
frontend/
  src/
    app/
      layout.tsx
      page.tsx
      globals.css
      login/page.tsx
      account/page.tsx
      fonts/Inter.ttf
      fonts/OFL.txt
    components/ui/button.tsx
    lib/api.ts
    lib/utils.ts
backend/
  app/
    main.py
    api/
      health.py
      auth.py
      dependencies.py
    core/
      config.py
      errors.py
      security.py
    db/
      base.py
      session.py
    models/
      user.py
      auth_session.py
    schemas/
      health.py
      auth.py
    services/auth.py
    repositories/
      users.py
      auth_sessions.py
    cli/create_master.py
    utils/
  tests/
    conftest.py
    test_foundation.py
    test_config.py
    test_auth.py
    test_auth_config.py
  alembic/
    env.py
    script.py.mako
    versions/20260910_01_users_sessions.py
  alembic.ini
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  Dockerfile
infra/
  compose.yaml
  .env.example
docs/
  architecture.md
  authentication.md
  authentication-files.md
  validation.md
```

Arquivos __init__.py, configurações do frontend e exemplos de ambiente foram
omitidos dessa árvore para facilitar a leitura.

A API é criada por create_app. Rotas, schemas, consultas e operações ficam separados.
Não há uma camada genérica de repositórios, arquitetura de microsserviços ou ORM
assíncrono. As sessões SQLAlchemy são síncronas, com commits explícitos nos serviços.
Não se usa Base.metadata.create_all para preparar o banco.

## 6. Fundação implementada

- Endpoint GET /health, retornando {"status":"ok"}.
- Configuração tipada por variáveis de ambiente.
- CORS preparado para o frontend.
- Tratamento centralizado de erros HTTP, validação e erros inesperados.
- Erros de validação não repetem valores enviados pelo cliente.
- Erros inesperados retornam mensagem genérica e são registrados no servidor.
- Base declarativa SQLAlchemy e dependência get_db.
- Alembic integrado à metadata dos modelos.
- Testes da fundação, lint e verificação de tipos.
- Dockerfile com aplicação executando como appuser.
- Compose com PostgreSQL, volume persistente e healthchecks.
- README e documentação de execução.

O /health é liveness da API: não verifica disponibilidade do PostgreSQL.

## 7. Modelos existentes

### User — tabela users

| Campo | Implementação |
| --- | --- |
| id | UUID, gerado pela aplicação |
| name | String de até 120 caracteres |
| email | String de até 320 caracteres, única |
| password_hash | Hash Argon2, sem retorno na API |
| role | MASTER, PROFESSIONAL ou STUDENT |
| is_active | Boolean, ativo por padrão |
| created_at | Timestamp com timezone |
| updated_at | Timestamp com timezone e atualização pelo ORM |

O e-mail é normalizado para minúsculas pelos schemas utilizados. O banco possui
UNIQUE e CHECK exigindo e-mail em minúsculas e sem espaços nas extremidades.
A role usa enum Python e constraint no banco, sem tipo enum nativo PostgreSQL.

### AuthSession — tabela auth_sessions

| Campo | Implementação |
| --- | --- |
| token_hash | SHA-256 do token aleatório, chave primária |
| user_id | FK para users.id, com ON DELETE CASCADE |
| created_at | Timestamp com timezone |
| expires_at | Timestamp com timezone |

Existem índices em user_id e expires_at.

Não existem outras entidades de negócio. A futura entidade Professional deverá
referenciar User e evitar repetir nome, e-mail, senha ou status que já pertençam a ele.

## 8. Autenticação implementada

O mecanismo utiliza sessão opaca persistida no PostgreSQL, não JWT.

1. O frontend envia email e password para POST /auth/login.
2. O backend verifica Argon2, existência do usuário e is_active.
3. Gera token aleatório com secrets.token_urlsafe(32).
4. Salva somente o hash SHA-256 do token e sua expiração.
5. Envia o token no cookie HttpOnly.
6. Requisições protegidas consultam sessão válida e usuário no banco.
7. Logout remove a sessão do banco e o cookie.

Características:

- Cookie SameSite=Lax, Path=/, sem Domain explícito.
- Sessão padrão de 3600 segundos, com expiração absoluta.
- Não há refresh token nem renovação automática.
- COOKIE_SECURE=true ativa Secure e nome __Host-nutramove_session.
- Em desenvolvimento HTTP, o nome é nutramove_session.
- A configuração production exige cookie seguro e origens HTTPS.
- Login troca a sessão anterior apresentada por aquele navegador.
- Sessões expiradas do usuário são removidas ao realizar um novo login.
- Não há persistência de tokens em localStorage.
- E-mail inexistente, senha incorreta e usuário inativo produzem a mesma mensagem 401.
- Login rejeita campos extras, incluindo role e user_id.
- Respostas públicas utilizam UserResponse, sem password_hash ou token em JSON.
- Respostas de sucesso de autenticação usam Cache-Control: no-store.

A escolha de sessões persistidas permite revogação imediata e consulta da role
atual sem introduzir infraestrutura adicional.

## 9. Endpoints reais

| Método | Endpoint | Entrada / resultado |
| --- | --- | --- |
| GET | /health | Público; 200 com status ok |
| POST | /auth/login | JSON email/password; 200 com UserResponse e cookie |
| GET | /auth/me | Sessão válida; 200 com UserResponse; caso contrário 401 |
| POST | /auth/logout | Revogação idempotente; 204 |

UserResponse contém: id, name, email, role, is_active e created_at.

Não existem endpoints /master, /professionals, /students, cadastro público,
recuperação de senha ou IA.

## 10. Autorização, CSRF e CORS

Dependências reutilizáveis:

- get_current_user: identifica usuário a partir do cookie e consulta o banco.
- CurrentUser: alias tipado para injeção desse usuário.
- require_roles(UserRole.MASTER): restringe acesso pela role consultada no backend.
- DbSession e AppSettings: aliases para as dependências comuns.
- require_trusted_origin: valida Origin contra CORS_ORIGINS.

O helper de autorização já foi testado com:

- MASTER: permitido.
- PROFESSIONAL e STUDENT: 403 em rota de teste exclusiva de MASTER.
- Não autenticado: 401.
- Mudança da role no banco: passa a valer na sessão já existente.
- Role e identificadores enviados pelo cliente: não concedem permissão.

Esses testes não significam que o módulo administrativo esteja implementado:
a rota exclusiva de MASTER usada nesses casos existe somente no app de testes.

POST /auth/login e POST /auth/logout exigem Origin confiável.
get_current_user também valida Origin em métodos que alteram dados.
O frontend usa credentials: include.

CORS permite atualmente GET e POST, Content-Type e a origem
http://localhost:3000. Quando forem criadas rotas PATCH/PUT, o próximo prompt deve
prever a ampliação mínima de CORS e os respectivos testes.

Importante para uso manual:

- http://127.0.0.1:3000 é outra origem, não liberada por padrão.
- O Swagger na porta 8000 não está autorizado por padrão para POST de autenticação.
- A política SameSite pressupõe frontend e API no mesmo site em produção, com HTTPS.
- Esconder UI administrativa não substitui dependências de autorização no backend.

## 11. Primeiro MASTER

Foi criado um comando administrativo interativo:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m app.cli.create_master
```

Alternativa dentro de backend/:

```powershell
.venv/Scripts/python.exe -m app.cli.create_master
```

Solicita nome, e-mail, senha e confirmação. A senha exige de 12 a 128 caracteres e
não é exibida nem passada como argumento de linha de comando. A role é fixada no
servidor como MASTER. E-mail duplicado é rejeitado.

Nenhuma conta padrão foi criada pela implementação. Não foi verificado neste
relatório se o usuário executou esse comando posteriormente.

## 12. Frontend disponível

- / redireciona para /login.
- /login verifica sessão existente e permite entrar pela API real.
- /account consulta /auth/me e exibe nome, e-mail, perfil e logout.
- Estados de carregamento, submissão, erro e sucesso.
- Redirecionamento para login quando a API rejeita a sessão.
- Cliente HTTP tipado em src/lib/api.ts.
- Layout responsivo, ícones Lucide e fonte Inter local.

Paleta solicitada, utilizada como referência visual:

| Nome | Cor |
| --- | --- |
| Nutra Green | #167D5A |
| Deep Green | #124C3A |
| Mint | #A8D8BD |
| Petrol Blue | #176B78 |
| Energy | #D5B85A |
| Canvas | #F6F8F6 |
| Surface | #FFFFFF |
| Ink | #1D2924 |
| Muted | #697770 |
| Border | #E1E8E3 |
| Danger | #C94B4B |

Não há dashboard MASTER, tabela de profissionais ou formulários de gestão.
A interface ainda não possui suíte automatizada de navegador.

## 13. Migration e banco

Migration existente:

- Arquivo: backend/alembic/versions/20260910_01_users_sessions.py.
- Revision: 20260910_01.
- down_revision: None.
- Cria users e auth_sessions, constraints e índices.
- Foi aplicada ao banco local na etapa de autenticação.
- Upgrade, downgrade e novo upgrade foram verificados somente em schema de teste.
- Alembic check não detectou divergências na validação anterior.

A próxima entidade deve receber uma nova migration dependente de 20260910_01.
Não editar esta revisão já aplicada para acrescentar Professional.

## 14. Testes e verificações anteriores

| Verificação | Último resultado registrado |
| --- | --- |
| pytest | 40 testes passaram, nenhum pulado |
| Ruff lint | Aprovado |
| Ruff formatação | 35 arquivos formatados |
| mypy strict | Nenhum erro em 35 arquivos |
| pip check | Nenhuma incompatibilidade |
| Biome | Aprovado em 14 arquivos |
| TypeScript | Aprovado |
| Build Next.js | Aprovado |
| Build Docker backend | Aprovado |
| Alembic | Upgrade/downgrade/check aprovados |
| Smoke HTTP no contêiner | /health 200 e /auth/me anônimo 401 |

Os testes de autenticação usam PostgreSQL real, no banco configurado, mas criam um
schema aleatório test_auth_*. Aplicam migrations e isolam cada teste com transação
e rollback. O schema é removido ao final. Não usam SQLite nem create_all.

Cobertura relevante:

- Login, consulta de conta e logout.
- Hash de senha e digest do token.
- Revogação e rotação de sessão.
- Expiração e token desconhecido.
- Usuário inativo e desativação durante sessão.
- Autorização por role e mudança de role no banco.
- Rejeição de campos extras no login.
- E-mail duplicado e constraint no banco.
- Proteção de origem e CORS com credenciais.
- Configuração segura de produção.
- Health e tratamento de erros da fundação.

Esses resultados não equivalem a auditoria de segurança completa ou aprovação para produção.

## 15. Comandos de validação para próximos prompts

Backend, dentro de backend/:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m pip check
```

Frontend, dentro de frontend/:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Compose, na raiz:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic current
docker compose --env-file infra/.env -f infra/compose.yaml exec -T backend python -m alembic check
```

Executar migrations novas exige revisar seu conteúdo e aplicar upgrade.
No Windows, npm.cmd evita a restrição de execução de scripts npm.ps1.
A opção no:cacheprovider contorna uma permissão do cache local do pytest; não pula testes.

## 16. Problemas encontrados e limitações

Problemas tratados:

- Autenticação ausente no checkout inicial: implementada após autorização.
- ESLint do scaffold sem suporte e incompatibilidade de plugins com atualização:
  adotado Biome, já funcional.
- Cliente de testes httpx depreciado pela versão atual do Starlette:
  adotado httpx2.
- Rede/Docker bloqueados pelo sandbox: operações necessárias executadas com autorização.
- Cache pytest com permissão negada: verificação final executada sem cache.
- Dependência desnecessária de effect apontada pelo Biome: fluxo de retry simplificado.

Aviso remanescente:

- DeprecationWarning interno do Starlette pelo alias anyio.abc.BlockingPortal.
  Não foi ocultado e não vem de uso desse alias no código do projeto.

Pendências técnicas:

- Limitação de tentativas de login antes de exposição pública.
- Observabilidade e requisitos operacionais de produção.
- Recuperação e troca de senha, MFA, conforme futuro escopo.
- Revogação de todas as sessões de um usuário.
- Limpeza periódica de sessões expiradas quando necessária.
- Testes de navegador para login/logout e fluxos administrativos.
- Lockfile de dependências transitivas Python.
- HTTPS, proxy reverso, backups, pipeline e deploy na VPS.

Atenção para desativação: hoje is_active=false impede acesso. Se alguém alterar o
banco para reativar o usuário, uma sessão antiga ainda não expirada pode voltar a
funcionar. O futuro fluxo administrativo deve revogar todas as sessões ao desativar
e testar que a reativação exige novo login.

## 17. Próximo escopo funcional já solicitado: MASTER + Professional

Ainda pendente de execução nesta base autenticada:

1. Criar Professional associado obrigatoriamente a User.
2. Usar relação consistente, preferencialmente 1:1 com FK e UNIQUE em user_id.
3. Reutilizar nome, e-mail, senha e status de User; não duplicar esses campos.
4. Adicionar specialty opcional e timestamps conforme o padrão existente.
5. Criar User e Professional na mesma transação, ou definir explicitamente as regras
   de vínculo com usuário já existente.
6. Fixar role PROFESSIONAL no backend; não aceitar promoção pelo cliente.
7. Implementar criar, listar, visualizar, buscar, editar e ativar/desativar/reativar.
8. Evitar exclusão física como fluxo normal.
9. Proteger todos os endpoints de gestão com require_roles(UserRole.MASTER).
10. Criar nova migration, preservando 20260910_01.
11. Implementar área MASTER responsiva com API real, estados completos e confirmação
    antes da desativação.
12. Testar permissões, duplicidade de e-mail, respostas sem password_hash, atomicidade
    de criação e revogação de sessões na desativação.

Não criar Professional como duplicata do User.
Não criar outro sistema de autenticação.
Não implementar alunos, dieta, treino ou IA nesse escopo.

## 18. Decisões que o próximo prompt precisa esclarecer

Estas questões ainda não foram implementadas e não devem ser tratadas como decisões prontas:

- Criação de profissional cria sempre um novo User ou também permite vincular um
  existente? Se permitir vínculo, como impedir vincular MASTER/STUDENT indevidamente?
- Como o profissional recebe a primeira senha? Não existe fluxo de convite ou
  recuperação; não solicitar envio de e-mail sem prever infraestrutura e autorização.
- Quais campos MASTER poderá editar e se poderá alterar e-mail.
- Padrão de endpoints administrativos e uso de PATCH para edição/status.
- Paginação, ordenação e campos incluídos na busca.
- Se specialty será texto livre nesta etapa.
- Como organizar a entrada da área MASTER após login sem criar rotas futuras fictícias.
- Se testes de navegador entram nesta etapa ou em uma validação dedicada.

Quando uma escolha simples puder ser assumida, o prompt deve explicitar a escolha e
seu limite, em vez de solicitar uma arquitetura ampla e indefinida.

## 19. Orientação para o chat que gerar os próximos prompts

Use este relatório como contexto, mas peça ao agente executor para confirmar o
estado atual dos arquivos antes de editar. Preserve alterações locais existentes.

Organize o trabalho em etapas revisáveis. Para cada prompt, especifique:

- Objetivo e o que fica fora do escopo.
- Arquivos e componentes existentes que devem ser reutilizados.
- Regras de dados e autorização.
- Comportamento de erro e transações.
- Migration necessária e critérios de validação.
- Testes mínimos e comandos de qualidade.
- Relato final com arquivos, decisões, riscos e resultados.
- Parada ao concluir a etapa, sem commit nem avanço automático.

Não interprete “roles disponíveis” como “módulos prontos”, “build passou” como
“fluxo validado em navegador” ou “autenticação implementada” como “produção pronta”.

## 20. Documentos de apoio no repositório

- README.md: instalação, execução e criação do primeiro MASTER.
- docs/architecture.md: organização atual.
- docs/authentication.md: comportamento de autenticação e limites.
- docs/authentication-files.md: arquivos criados/modificados na autenticação.
- docs/validation.md: histórico de verificações da fundação e autenticação.

Este relatório não contém senhas, tokens ou conteúdo dos arquivos .env.
