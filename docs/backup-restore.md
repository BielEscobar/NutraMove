# Backup e restore do PostgreSQL e das fotos privadas

Os scripts [backup-postgres.sh](../infra/scripts/backup-postgres.sh), [verify-restore.sh](../infra/scripts/verify-restore.sh) e [verify-uploads-restore.sh](../infra/scripts/verify-uploads-restore.sh) são para a VPS Linux com `infra/.env.prod` preenchido e stack saudável. **Não foram executados em produção.** A retenção abaixo é técnica/provisória; o controlador deve aprovar a política aplicável a dados de saúde, fotos e backups.

## Backup

```bash
sudo install -d -m 700 -o "$(id -un)" -g "$(id -gn)" /srv/nutramove/backups
NUTRAMOVE_BACKUP_DIR=/srv/nutramove/backups bash infra/scripts/backup-postgres.sh
```

Uma execução produz **dois arquivos com o mesmo timestamp**: `daily/nutramove-YYYYMMDDTHHMMSSZ.dump` e `daily/private_uploads_YYYYMMDDTHHMMSSZ.tar.gz`, cada um com SHA-256. O backend é parado de forma controlada durante a captura dos dois recursos e reiniciado também se houver falha. Isso cria uma janela breve de indisponibilidade da API; agende fora do horário de uso. O script usa `pg_dump -Fc`, valida o catálogo com `pg_restore --list`, lê o volume privado montado pelo backend em contêiner isolado sem rede e valida o arquivo tar. Só anuncia sucesso após os dois arquivos e o retorno saudável do backend. Não registra fotos ou segredos no log. Não inclui cache ou imagens Docker.

Aos domingos copia ambos os arquivos e checksums para `weekly/`. A retenção local provisória remove pares diários com mais de 6 dias e semanais com mais de 27 dias, cerca de 7 diários/4 semanais. O diretório de backup deve ficar fora dos volumes de banco/fotos, com acesso `0700`, espaço e falhas monitorados.

Agendar diariamente no **cron do host**, por exemplo `20 2 * * * /usr/bin/env NUTRAMOVE_BACKUP_DIR=/srv/nutramove/backups /bin/bash /srv/nutramove/repo/infra/scripts/backup-postgres.sh >> /srv/nutramove/backup-status.log 2>&1`, ajustando o caminho absoluto. Monitorar falha e crescimento de disco; o cron não substitui monitoramento. Copiar **os dois arquivos e seus checksums** para armazenamento criptografado fora da VPS, como object storage ou servidor externo com acesso restrito, antes da abertura a dados reais. Guardar chaves fora do repositório e testar periodicamente a recuperação da cópia externa.

## Restore de verificação, sem tocar na produção

```bash
bash infra/scripts/verify-restore.sh /srv/nutramove/backups/daily/nutramove-YYYYMMDDTHHMMSSZ.dump
# Opcional: passar UUID de conta sintética conhecida como segundo argumento.
```

O script verifica checksum quando presente, cria banco temporário `nutramove_restore_*`, restaura com `pg_restore --exit-on-error`, confirma revisão Alembic e contagem de `users`, opcionalmente exige a conta sintética indicada, e remove **somente o banco temporário criado por ele** ao sair. Nunca restaura sobre o banco de produção. Registrar data, nome do backup, revisão, contagem e resultado sem e-mail, senha ou dados clínicos. Repetir após mudança importante e periodicamente, inclusive a partir do armazenamento externo. Em teste local, usar dados sintéticos isolados.

Verificar o arquivo de fotos correspondente com um **volume Docker temporário**, sem montar nem alterar `private_uploads_prod`:

```bash
bash infra/scripts/verify-uploads-restore.sh /srv/nutramove/backups/daily/private_uploads_YYYYMMDDTHHMMSSZ.tar.gz
```

O verificador confere SHA-256, restaura apenas no volume recém-criado, rejeita entradas inseguras do tar, compara estrutura e SHA-256 de cada arquivo restaurado e remove somente esse volume temporário. Nomes/chaves não são impressos. Execute as duas verificações para o **mesmo timestamp** e periodicamente a partir da cópia externa.

Para recuperação real, interromper writes, obter aprovação operacional e selecionar **o par** do mesmo timestamp, preferencialmente da cópia externa. Verificar checksums; restaurar PostgreSQL em banco/volume novo; restaurar o tar em **novo volume privado** usando `python -m app.cli.private_uploads_archive verify <arquivo> <diretório vazio>` na imagem backend aprovada; ajustar recursivamente a propriedade dos arquivos e diretórios restaurados ao usuário `appuser` antes de montar o volume no backend. Nunca executar essa extração contra o volume ativo. Validar `alembic current/check`, a correspondência entre metadados do banco e arquivos, então iniciar a aplicação com o novo banco e o novo volume. Fazer login sintético e confirmar acesso autenticado às fotos. Só depois alternar tráfego. Um dump lógico não cobre transações posteriores; RPO/RTO e retenção precisam de decisão operacional. Não usar `docker compose down -v` nem `pg_restore --clean` no banco ativo.
