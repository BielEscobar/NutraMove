# Dashboards e navegação por perfil — Dia 5

Implementado em 10 de setembro de 2026. Preserva os módulos anteriores e suas
alterações locais sem commit. Não inclui Diet, Workout, IA ou configurações editáveis.

## Endpoints e consultas

| Endpoint GET | Papel | Resposta |
| --- | --- | --- |
| /master/dashboard | MASTER | Profissionais totais/ativos; alunos totais, ativos, pendentes, inativos, rejeitados e sem profissional |
| /professional/dashboard | PROFESSIONAL | Contagens da própria carteira por status e até cinco cadastros mais recentes |
| /student/dashboard | STUDENT | Nome, status, objetivo/complemento, peso, altura e nome do responsável |

Todos usam a autenticação existente, require_roles e Cache-Control: no-store.
Identificadores de query enviados pelo cliente são ignorados: o escopo deriva
exclusivamente do User autenticado. Não há parâmetro para selecionar outra carteira
ou aluno. Role inadequada recebe 403; anônimo recebe 401.
Profissional sem entidade Professional recebe 403; aluno sem Student recebe 404.

As contagens usam COUNT e FILTER no PostgreSQL. student_metrics reutiliza
scoped_query, projetando somente colunas necessárias para a agregação.
O vínculo Professional.id é resolvido pelo User.id da sessão.
Profissionais são contados pelo summary já existente.
Não há listas completas carregadas para contar em Python ou no frontend.

Os recentes usam a mesma consulta com ownership e LIMIT 5, ordenados por
created_at e UUID decrescentes. Retornam somente id, nome, status e data.
São últimos cadastros, sem alegar atividade, evolução ou histórico inexistente.
As datas refletem o campo created_at; em empates o UUID estabiliza a ordenação.
Um teste verifica que o dashboard profissional usa no máximo cinco SELECTs,
incluindo autenticação, resolução do profissional e consultas de dados, sem N+1.

Os números de alunos usam Student.status, independentemente de User.is_active;
os serviços anteriores mantêm os dois coerentes. Profissionais ativos usam
User.is_active. Dados alterados diretamente no banco não executam regras de serviço.
Não há snapshot histórico, cache de métricas ou polling automático.

O dashboard do aluno reutiliza a consulta própria, mas retorna schema mínimo:
sem e-mail, telefone, nascimento, notas, restrições alimentares, hash ou token.
O perfil completo continua disponível, autorizado, por GET /students/me.

## Layout e componentes

AppShell centraliza consulta /auth/me, guarda por perfil, sidebar, cabeçalho,
identificação e logout. A navegação de outro perfil redireciona para a área real
do usuário. O backend continua responsável pela autorização.

- MASTER: Dashboard, Profissionais e Alunos.
- PROFESSIONAL: Dashboard e Meus alunos.
- STUDENT: Início e Meu perfil.
- Todos: Minha conta no cabeçalho e logout direto.

Configurações foram omitidas porque não existe funcionalidade editável correspondente.
Não foram criadas páginas vazias de configuração nem links quebrados.
A página /account existente permanece acessível.

MetricCard e EmptyState são componentes pequenos compartilhados.
ManagementDashboard reutiliza a estrutura visual entre MASTER e PROFESSIONAL.
LoadingState, ErrorState e useApiResource existentes foram reutilizados.
RoleLayout permanece como alias de AppShell para compatibilidade, sem layout duplicado.
Não foi criado um design system nem adicionada dependência de gráficos.

Sidebar ampla a partir de 1280 px, compacta de 768 a 1279 px e menu superior
adaptado abaixo de 768 px. Cards reorganizam colunas. Navegação, logout e botões
principais têm altura mínima de 44 px. Tabelas existentes mantêm scroll local.
Paleta, Inter local e Lucide foram preservados; há link de pular para o conteúdo.

## Comportamento após login

POST /auth/login estabelece sessão; em seguida GET /auth/me confirma a identidade:
MASTER → /master; PROFESSIONAL → /professional; STUDENT → /student.
Não se usa role manual em localStorage. A verificação de sessão ao abrir /login
utiliza a mesma função homeForRole.

O aluno ativo vê apenas dados existentes e estados sem ação: Meu treino e Minha
dieta ainda não disponíveis; Minha evolução em preparação.
Pendentes recebem a mensagem solicitada de cadastro em análise; rejeitados têm
estado próprio. Inativos normalmente recebem 401, pois a desativação bloqueia
a sessão. GET /student/dashboard não altera status ou cria planos.
O conteúdo detalhado anterior foi preservado em /student/profile.

Dashboards têm loading, erro com retry, dados e estados vazios pertinentes.
Carteira vazia apresenta contagens zero e orientação. Aluno sem cadastro recebe
erro apropriado; não se inventa um perfil. API indisponível não quebra a página.

## Arquivos criados

Backend:
- backend/app/schemas/dashboard.py: schemas específicos.
- backend/app/repositories/dashboards.py: agregações e últimos cadastros.
- backend/app/api/dashboards.py: três endpoints protegidos.
- backend/tests/test_dashboards.py: autorização, métricas, isolamento e consultas.

Frontend:
- frontend/src/components/app-shell.tsx.
- frontend/src/components/dashboard/metric-card.tsx.
- frontend/src/components/dashboard/management-dashboard.tsx.
- frontend/src/lib/dashboard.ts.
- frontend/src/app/professional/page.tsx.
- frontend/src/app/student/profile/page.tsx.

Documentação: docs/dashboards.md.

## Arquivos modificados nesta etapa

- backend/app/main.py: registro do router de dashboards.
- frontend/src/app/master/layout.tsx, professional/layout.tsx e student/layout.tsx:
  wrappers do layout compartilhado.
- frontend/src/app/master/page.tsx: dashboard com métricas globais reais.
- frontend/src/app/student/page.tsx: dashboard resumido.
- frontend/src/components/students/role-layout.tsx: alias compatível.
- frontend/src/lib/students.ts: destino PROFESSIONAL atualizado.
- frontend/src/app/login/page.tsx: confirmação por /auth/me após login.
- frontend/src/app/globals.css: altura mínima dos botões compartilhados.
- frontend/src/components/master/resource-state.tsx: retry com área de toque maior.
- README.md, docs/architecture.md, docs/validation.md e
  docs/relatorio-contexto-proximos-prompts.md: documentação atualizada.

A etapa não precisou de camada de serviço adicional: são somente leituras com
regras de escopo existentes e schemas explícitos. Não alterou modelos nem migrations.
A revisão do banco permanece 20260910_03. Alterações anteriores no Git foram preservadas.

## Validação

- pytest: 185 testes aprovados, nenhum pulado.
- Ruff check e Ruff format --check: aprovados.
- mypy strict: 53 arquivos, sem erros.
- pip check: sem incompatibilidades.
- Biome: 48 arquivos, aprovado.
- TypeScript e build Next.js: aprovados.
- Build Docker e Compose config --quiet: aprovados.

Chrome headless/CDP, com dados sintéticos em schema PostgreSQL isolado:
- Login e destino correto dos três papéis.
- Anônimo redirecionado e área de papel errado redirecionada.
- Logout revoga acesso (/auth/me retorna 401).
- Navegação por todos os links dos menus, sem páginas 404.
- Dashboards carregados com respostas 200 da API real.
- Falha temporária da API simulada por bloqueio no navegador e retry com recuperação.
- Carteira vazia, aluno pendente e rejeitado.
- 1366, 1024, 768 e 375 px em cada dashboard, sem overflow horizontal.
- Áreas de toque de navegação/logout verificadas; capturas representativas dos
  quatro tamanhos inspecionadas visualmente.
- Nenhuma exceção JavaScript não tratada.

É uma verificação pontual de navegador, não uma suíte E2E grande instalada.
Nenhum mock permanente foi adicionado. Não equivale a auditoria completa de
acessibilidade, desempenho ou segurança.
O DeprecationWarning interno Starlette/AnyIO continua visível. Git informa LF/CRLF.

## Limites e etapas futuras

Configurações editáveis, Diet, Workout, evolução, reavaliações e IA continuam
fora do escopo e dependem de novo pedido. Nenhum botão de geração foi adicionado.
A navegação compartilhada permite acrescentar módulos reais futuramente sem
reconstruir os três layouts. O Dia 6 não foi iniciado nem seu escopo presumido.

Continuam os débitos anteriores: proteção contra abuso no login/cadastro público,
recuperação de senha, política de dados, suíte E2E persistente e infraestrutura
de produção. Os dashboards não tornam a aplicação pronta para exposição pública.
