# Notificações internas (Dia 10)

Notification pertence ao User autenticado. A inbox comum permite listar com paginação e filtro unread_only, consultar item, contar não lidas por SQL COUNT, marcar uma ou todas como lidas. Outro User, inclusive MASTER, não acessa a inbox alheia. Ordenação: created_at DESC, id DESC.

Eventos integrados: DietVersion e WorkoutVersion aprovadas; ReevaluationRequest criada, em análise, concluída e cancelada pelo Professional; Information publicada; Student vinculado aguardando aprovação. Os textos são fixos e curtos. Não incluem conteúdo de planos, motivo de reavaliação, dados físicos nem links arbitrários. O frontend mapeia tipos conhecidos para rotas próprias.

As notificações são inseridas dentro da transação do evento. Publicação geral usa INSERT SELECT para alunos ACTIVE com User ativo; rascunhos não notificam. Restrição única por usuário, tipo e recurso previne duplicidade em um evento. O sino mostra a contagem; a página de inbox contém estado textual, links seguros e ações de leitura.

Não há push, e-mail, SMS, WhatsApp, fila ou agendamento. A futura transferência mantém notificações no User; acesso a recursos antigos deverá ser reavaliado então.
