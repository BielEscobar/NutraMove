# Backup e restore do PostgreSQL

Os scripts [backup-postgres.sh](../infra/scripts/backup-postgres.sh) e [verify-restore.sh](../infra/scripts/verify-restore.sh) são para a VPS Linux com `infra/.env.prod` já preenchido, Docker Compose e stack `db` healthy. **Não foram executados em produção.** A retenção abaixo é apenas técnica/provisória; o controlador deve aprovar a política aplicável a dados de saúde, auditoria e backups.

## Backup

```bash
sudo install -d -m 700 -o "$(id -un)" -g "$(id -gn)" /srv/nutramove/backups
NUTRAMOVE_BACKUP_DIR=/srv/nutramove/backups bash infra/scripts/backup-postgres.sh
```

O script usa `pg_dump -Fc` dentro do contêiner e grava no host em `daily/nutramove-YYYYMMDDTHHMMSSZ.dump`, com arquivo SHA-256 ao lado. Faz escrita temporária, verifica catálogo `pg_restore --list` e só então move ao nome final. Aos domingos copia para `weekly/`. Remove dumps gerados há mais de 6 dias na pasta diária e 27 na semanal, inclusive checksums; são aproximadamente 7 diários e 4 semanais. Não inclui volume, cache ou imagens Docker. O diretório de backup deve ser fora do volume principal do PostgreSQL, acesso `0700`, filesystem confiável e espaço monitorado.

Agendar diariamente no **cron do host**, por exemplo `20 2 * * * /usr/bin/env NUTRAMOVE_BACKUP_DIR=/srv/nutramove/backups /bin/bash /srv/nutramove/repo/infra/scripts/backup-postgres.sh >> /srv/nutramove/backup-status.log 2>&1`, ajustando o caminho absoluto. Monitorar falha e crescimento de disco; o cron não substitui monitoramento. Fazer cópia criptografada e com retenção controlada para armazenamento fora da VPS antes da abertura a dados reais. Guardar chaves e credenciais fora do repositório e testar recuperação dessa cópia externa.

## Restore de verificação, sem tocar na produção

```bash
bash infra/scripts/verify-restore.sh /srv/nutramove/backups/daily/nutramove-YYYYMMDDTHHMMSSZ.dump
# Opcional: passar UUID de conta sintética conhecida como segundo argumento.
```

O script verifica checksum quando presente, cria banco temporário `nutramove_restore_*`, restaura com `pg_restore --exit-on-error`, confirma revisão Alembic e contagem de `users`, opcionalmente exige a conta sintética indicada, e remove **somente o banco temporário criado por ele** ao sair. Nunca restaura sobre o banco de produção. Registrar data, nome do backup, revisão, contagem e resultado sem e-mail, senha ou dados clínicos. Repetir após mudança importante e periodicamente, inclusive a partir do armazenamento externo. Em teste local, usar dados sintéticos isolados.

Para recuperação real após perda de banco, interromper writes, obter aprovação operacional, preservar evidências, selecionar backup e ponto de recuperação, verificar checksum, criar banco/volume de destino novo e restaurar nele. Validar schema, conta sintética, integrações e `alembic current` antes de alternar o backend. Um dump lógico não garante recuperação de transações posteriores; RPO/RTO precisam ser definidos com o responsável. Não usar `docker compose down -v` ou `pg_restore --clean` diretamente no banco ativo.
