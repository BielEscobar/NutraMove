# Informativos (Dia 10)

O Professional cria rascunhos com título, categoria controlada (INFO, TIP, NOTICE, GUIDANCE), conteúdo de 10 a 10000 caracteres e audiência geral ou um aluno da própria carteira. O vínculo com Professional vem da sessão. O backend valida qualquer Student informado e devolve 404 para recursos fora da carteira.

O fluxo é DRAFT → PUBLISHED → ARCHIVED, ou DRAFT → ARCHIVED. Somente DRAFT pode ser editado; alterações exigem `expected_revision` para evitar sobrescrita concorrente. A publicação registra `published_at` e gera notificações na mesma transação. Informativos publicados não são apagados pela API.

O Student vê somente PUBLISHED da carteira atual, gerais ou destinados a ele. MASTER consulta administrativamente, sem mutações. A listagem é paginada e aceita categoria; a consulta profissional e MASTER também aceita status, student_id e general_only. O frontend possui lista, filtros, editor de rascunhos, publicação, arquivamento e leitura por perfil.

Na futura transferência de Student, será preciso definir acesso a informativos da carteira anterior e rever o destino de informativos individuais. Nenhuma transferência foi implementada aqui.
