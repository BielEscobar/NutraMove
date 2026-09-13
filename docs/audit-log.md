# AuditLog administrativo — Dia 11

AuditLog é append-only na API normal. Registra exclusivamente STUDENT_ASSIGNED e STUDENT_TRANSFERRED neste Dia. Cada linha guarda UUID, ator User, ação enum, tipo/recurso STUDENT, Professional anterior/novo, motivo administrativo e timestamp. Os IDs e FKs RESTRICT preservam interpretação histórica após desativação; não há snapshot clínico, cookie, senha ou payload inteiro.

MASTER consulta `GET /master/audit-logs` e `GET /master/audit-logs/{id}`. A listagem é paginada (20 por padrão, máximo 100), ordenada por created_at/id descendentes, com filtros action, resource_id e actor_user_id. Joins trazem nomes do ator e dos Professionals em uma consulta, sem N+1. Professional e Student não têm acesso; não existem endpoints de edição ou exclusão.

A migration 20260913_09 depende de 20260912_08 e cria `audit_logs`, checks, FKs e índices. O serviço de transferência cria a linha na mesma transação da mudança Student. Falha de inserção desfaz ambas as alterações.
