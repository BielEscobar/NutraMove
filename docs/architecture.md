# Fundação do NUTRAMOVE

## Organização

Um repositório com aplicações independentes. Frontend e backend têm dependências,
configurações e processos separados. Não há regras de negócio nesta etapa.

| Pasta | Finalidade |
| --- | --- |
| frontend/src/app | Rotas e layouts do Next.js (App Router). |
| frontend/src/components/ui | Componente Button do scaffold shadcn/ui e futuros componentes necess?rios. |
| frontend/src/lib | Utilitários do frontend, incluindo composição de classes CSS. |
| backend/app/api | Rotas HTTP; atualmente apenas GET /health. |
| backend/app/core | Configuração por ambiente e tratamento de erros. |
| backend/app/db | Base declarativa e ciclo de vida das sessões SQLAlchemy. |
| backend/app/models | Futuros modelos de persistência. |
| backend/app/schemas | Contratos Pydantic de entrada e saída. |
| backend/app/services | Futuras operações e regras de negócio. |
| backend/app/repositories | Futuras consultas ao banco, sem abstração genérica antecipada. |
| backend/app/utils | Utilitários pequenos, quando necessários. |
| backend/tests | Testes automatizados isolados, sem exigir PostgreSQL. |
| backend/alembic | Configuração e futuras revisões do banco. |
| infra | Compose e configuração local dos contêineres. |
| docs | Decisões e documentação técnica. |

## Backend

A fábrica create_app permite criar uma API com configurações explícitas nos testes.
Pydantic Settings lê backend/.env e variáveis do processo; estas têm precedência.
DATABASE_URL é obrigatória e exige o driver postgresql+psycopg.

GET /health retorna {"status":"ok"} e verifica somente a disponibilidade da API.
Não consulta PostgreSQL: não é um teste de prontidão do banco.

O SQLAlchemy 2.0 usa sessões síncronas, uma por requisição quando get_db for usado.
A conexão só é criada quando necessária. A sessão fecha ao terminar e desfaz
transações pendentes. Commits futuros devem ser explícitos na operação que controla
a transação. Nenhuma tabela é criada automaticamente.

Alembic usa a mesma configuração de banco e Base.metadata. Quando houver modelos,
eles deverão ser importados em app/models/__init__.py. Não há revisão inicial vazia:
as migrations de negócio serão criadas junto dos respectivos modelos.

Erros HTTP usam um envelope error. Erros de validação retornam localização e tipo,
sem ecoar entradas. Erros inesperados retornam mensagem genérica e são registrados
no log do servidor. Debug está desativado.

CORS permite inicialmente GET e Content-Type para http://localhost:3000, sem
credenciais. Novos métodos/cabeçalhos serão liberados quando houver endpoints que
precisem deles. CORS é uma regra do navegador, não autorização de acesso à API.
Nenhuma autenticação ou autorização de negócio foi implementada.

## Frontend

A página inicial é estática. Tailwind e shadcn/ui estão preparados para componentes
futuros, sem um catálogo de componentes antecipado. Lucide fornece o ícone inicial.
Não há chamadas à API, estados globais ou biblioteca HTTP adicional.
NEXT_PUBLIC_API_URL documenta o endereço público para uso futuro; variáveis
NEXT_PUBLIC_* são públicas no bundle e nunca devem conter secrets.
São usadas fontes do sistema, sem download de fontes durante o build.

## Infraestrutura

O Compose desta etapa executa backend e PostgreSQL 17. O frontend roda localmente
com npm para manter seu scaffold mínimo e o desenvolvimento simples. As portas
publicadas são vinculadas a 127.0.0.1. Os dados usam volume nomeado.
A API espera o healthcheck do PostgreSQL antes de iniciar, mas não executa migrations
automaticamente. O contêiner do backend executa com usuário sem privilégios de root.

Este Compose é para desenvolvimento local. Deploy na Hostinger, TLS, proxy reverso,
backups e pipeline de produção ficam para uma etapa autorizada específica.
develop é a branch de desenvolvimento; main é reservada para produção.

## Referências oficiais consultadas

- [Next.js: instalação](https://nextjs.org/docs/app/getting-started/installation)
- [shadcn/ui: instalação](https://ui.shadcn.com/docs/installation/manual)
- [FastAPI: CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [FastAPI: erros](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [SQLAlchemy: sessões](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Alembic: tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

As depend?ncias Python diretas est?o fixadas nos requirements; as transitivas ainda
s?o resolvidas pelo pip. O frontend versiona package-lock.json para uso com npm ci.
