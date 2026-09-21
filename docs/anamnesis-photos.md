# Anamnese e evolução fotográfica

A anamnese atual do Student reúne identificação, dados corporais, objetivo, rotina, experiência e disponibilidade de treino, saúde informada e alimentação. Idade é calculada a partir de `birth_date`; não existe coluna de idade. Campos estruturados usam enums para sexo, objetivo, experiência, local de treino e habilidade culinária. `goal_detail` é obrigatório apenas para `OTHER`; `injury_description` é obrigatório quando `has_injury=true`.

O onboarding público usa sete etapas: conta; objetivo e dados corporais; rotina e treino; alimentação; saúde e limitações; fotos; revisão. O envio com fotos usa `POST /students/register-with-photos` e exige exatamente uma imagem FRONT e uma SIDE. O endpoint JSON anterior permanece compatível com integrações V1, mas a interface oficial exige as fotos.

## Fotos privadas

`ProgressPhotoSet` representa um instante do histórico, com origem `INITIAL` ou `REEVALUATION`; `ProgressPhoto` guarda posição, MIME, tamanho e chave aleatória. JPEG, PNG e WebP são aceitos após verificação de extensão, MIME, assinatura binária e limite configurável de 8 MiB. Nome original, caminho interno e chave de storage não aparecem na API.

Os bytes ficam em `PRIVATE_UPLOAD_DIR`, por padrão `backend/private_uploads`, abstraídos pelo serviço `progress_photos`. Docker usa volume nomeado persistente. A migração futura para object storage fica isolada nesse serviço. O backup de produção precisa incluir o volume `private_uploads_prod` junto do banco.

Student lê somente os próprios conjuntos e o Professional atual somente a própria carteira. A transferência revoga o acesso do Professional anterior porque cada consulta usa o vínculo atual. MASTER não possui rota de conteúdo, por minimização. As imagens não ficam em `public/`, não têm URL permanente e são entregues por endpoints autenticados com `no-store`.

Fotos não são enviadas à NutraMove AI e não entram em logs. Não há reconhecimento facial, biometria ou processamento automático de imagem.

Na transferência de carteira, a listagem e o download binário retornam 404 ao Professional anterior e passam a ser acessíveis ao Professional atual. Se a segunda gravação falhar após a primeira, o serviço remove os arquivos já escritos antes de propagar a falha; cadastro e reavaliação mantêm rollback do banco.
