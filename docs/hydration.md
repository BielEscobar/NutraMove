# Hidratação — Dia 9

Implementado em 11 de setembro de 2026.

## Dados e unidade

`WaterRecord` possui UUID, `student_id`, `amount_ml`, `consumed_at` e `created_at`.
A quantidade é um inteiro de 1 a 10000 ml por registro. Booleanos, strings numéricas,
frações, zero e negativos são rejeitados pelo schema. O banco também verifica o intervalo.
Esse limite protege a consistência dos dados; não constitui orientação clínica.

`Student.water_goal` continua em **litros/dia**, sem migration de unidade. A resposta
converte a meta para mililitros inteiros, arredondando para o mililitro mais próximo.
Meta nula, zero ou arredondada para zero produz `goal_ml`, `remaining_ml` e `percentage`
nulos. Nenhuma fórmula de recomendação foi criada. `approximate_water_intake` do
onboarding permanece uma informação separada do histórico registrado.

Professional altera a meta pelo PATCH de Student já existente, somente na própria
carteira. A página de hidratação oferece esse formulário. MASTER mantém a capacidade
administrativa de editar a meta pelo detalhe de Student; suas novas telas de
hidratação são apenas de consulta. Student não possui endpoint de edição da meta.

## Horários e resumo

`consumed_at` aceita timestamp com timezone, opcional; quando omitido usa o instante
atual UTC. Datas sem offset são rejeitadas. Aceita até cinco minutos no futuro para
pequenas diferenças de relógio. Não há limite retroativo nesta versão.

`BUSINESS_TIMEZONE` é uma configuração IANA validada no backend, com padrão
`America/Sao_Paulo`. Pode ser definida em backend/.env ou no ambiente do Compose.
Não foi criado timezone por usuário. O ambiente Windows já possui tzdata como
dependência do Psycopg; o contêiner fornece a base de fusos do sistema. Nenhuma
nova dependência foi necessária.

O backend determina a data de negócio e transforma os limites locais de início/fim
do dia em instantes UTC. As consultas usam `>= início` e `< próximo dia`.
Isso também trata dias com duração diferente de 24 horas em fusos com horário de verão.
O resumo e seus registros usam a mesma data calculada para a resposta.
O formulário converte o horário do dispositivo para ISO com offset UTC; registros
são exibidos no timezone informado pela API.

Consumo diário é `SUM(amount_ml)` no PostgreSQL. O histórico agrupa pela data local
com `timezone(...)`, `CAST AS DATE` e `SUM`. Datas sem lançamento são preenchidas com
zero na resposta. Não existem tabelas de totais diários nem percentuais persistidos.

Restante = `max(0, meta - consumo)`; percentual = consumo/meta × 100, com uma casa decimal.
Pode superar 100%; a barra visual é limitada a 100%, e o texto preserva o percentual real.
Histórico oferece hoje, 7 e 30 dias, incluindo hoje. A meta atual não é apresentada
como se fosse uma meta histórica de cada dia.

## Endpoints

Todos exigem sessão e role correspondente. Mutações exigem Origin confiável.

| Método | Rota | Finalidade |
| --- | --- | --- |
| POST | /student/water-records | Registrar consumo próprio; 201. |
| GET | /student/hydration/summary | Resumo compacto do dia, sem registros; dashboard. |
| GET | /student/hydration | Resumo e registros do dia paginados. |
| GET | /student/hydration/history?days=7 | Histórico agregado; days aceita 1, 7 ou 30. |
| GET | /professional/students/{id}/hydration | Dia do aluno da carteira. |
| GET | /professional/students/{id}/hydration/history | Histórico da carteira. |
| GET | /master/students/{id}/hydration | Consulta administrativa. |
| GET | /master/students/{id}/hydration/history | Histórico administrativo. |

Registros do dia: `page` a partir de 1, `page_size` padrão 20, máximo 100;
ordenação por consumo decrescente e UUID como desempate. Totais consideram todo o dia,
independentemente da página. Respostas de sucesso usam `Cache-Control: no-store`.

## Autorização e privacidade

WaterRecord pertence a Student, sem `professional_id` duplicado. Student é obtido
pelo User da sessão; campos extras de identidade e autorização no POST são rejeitados.
Profissionais consultam apenas Students do vínculo atual, por meio do escopo existente.
Carteira alheia e UUID inexistente produzem 404. Anônimo recebe 401 e role incompatível 403.

Aluno pendente ou rejeitado que ainda possui conta ativa pode registrar seu consumo
pessoal e consultar o histórico. Reavaliações possuem regra mais restrita, descrita no
outro módulo. Conta inativa continua bloqueada pela autenticação.

A API não retorna user_id, professional_id, senha ou tokens nestes schemas.
Não há logs de consumo nem valores SQL; as proteções de sessão, erros e logs anteriores
foram preservadas. Motivos e quantidades não são enviados a serviços externos.

## Interface

- Student: menu Hidratação, atalhos 250/300/500 ml, valor e horário opcionais, progresso
  com texto, lista paginada e gráfico Recharts com valores alternativos em texto.
- Dashboard Student: card Água hoje usa somente `/hydration/summary`.
- Professional: detalhe do aluno → Hidratação → consulta e configuração da meta.
- MASTER: detalhe do aluno → Hidratação → consulta.
- Labels, botões textuais, feedback de erro/sucesso e bloqueio de envio simultâneo.

## Persistência e arquivos

Migration `20260911_07`, dependente de `20260911_06`, cria `water_records` e
`reevaluation_requests`. Índice `(student_id, consumed_at)` atende intervalos por aluno.
FK restringe exclusão de Student; nenhuma migration anterior foi modificada.

Backend: models/hydration.py, schemas/hydration.py, repositories/hydration.py,
services/hydration.py, api/hydration.py, core/time.py e tests/test_hydration.py.
Frontend: lib/hydration.ts, components/hydration/* e páginas hydration de cada perfil.
Integração: core/config.py, .env.example, infra/compose.yaml, models/__init__.py,
main.py, AppShell, StudentDetail e dashboard Student.

## Limitações

Não há DELETE, edição de registros, lembretes, histórico de metas, timezone individual,
recomendação automática ou cron. O usuário deve conferir o lançamento antes de enviar.
A proteção de duplo clique é de interface; POST de água não tem chave de idempotência
para repetição após falha de rede. Avaliar isso antes de adicionar sincronização offline.
A página não faz polling: totais são atualizados ao carregar ou após salvar.

Validação, resultados de navegador e pontos de atenção estão em [validation.md](validation.md)
e no [relatório do Dia 9](dia9-relatorio.md).
