# Changelog

## 1.0.0 — release preparada

Primeira versão do NutraMove, com:

- autenticação por sessão e áreas separadas para MASTER, Professional e Student;
- gestão de profissionais, cadastro/aprovação de alunos e transferência com AuditLog;
- dietas e treinos versionados, revisão profissional e publicação ao aluno;
- avaliações, evolução física, hidratação e solicitações de reavaliação;
- informativos e notificações internas;
- NutraMove AI opcional para rascunhos de dieta e treino, desabilitada por padrão e sem publicação automática;
- hardening de segurança, rate limiting, documentação de privacidade e configuração de produção;
- stack Docker com Caddy, PostgreSQL persistente, runbooks de deploy, backup/restore e rollback.

O deploy público depende de configuração e validação da VPS, DNS, TLS, backup externo e smoke autenticado.
