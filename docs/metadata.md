# Esquema de metadados do dataset

Os arquivos de metadados utilizados pela CLI `oratiotranscripta-annotate` seguem o esquema abaixo, modelado pela classe `DatasetMetadata`.

## Campos principais

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `project` | string | Nome do projeto ou coleção ao qual o registro pertence. |
| `event` | string | Identificação do evento, entrevista ou sessão gravada. |
| `participants` | lista ou mapeamento | Lista de participantes ou objeto com participantes nomeados. Cada participante pode informar `name`, `role` (função) e `aliases` (variações do nome). |
| `dates` | lista de strings | Datas relevantes para o registro (ex.: gravação, publicação). |
| `coverage` | objeto | Informações de cobertura espacial/temporal ou outra granularidade necessária. |
| `license` | string | Licença aplicável ao material. |
| `editors` | lista de strings | Pessoas responsáveis pela edição ou revisão dos dados. |

Os arquivos podem ser escritos em JSON ou YAML (qualquer YAML válido é aceito). Quando `participants` é um objeto mapeado, a chave é usada como nome padrão caso o campo `name` não seja informado.

## Participantes e aliases

Cada participante pode listar aliases para permitir variações na transcrição. Durante a anotação, todos os `speaker` encontrados no transcript precisam existir na lista de participantes (considerando aliases). Caso algum nome não seja encontrado, a execução é interrompida com uma mensagem listando os termos ausentes.

Exemplo em YAML:

```yaml
project: "Arquivo Histórico"
event: "Mesa redonda"
participants:
  maria:
    role: "Mediadora"
    aliases: ["M.", "Maria S."]
  joao:
    name: "João"
    role: "Convidado"
    aliases: ["J."]
dates:
  - "2024-02-10"
coverage:
  spatial: "Brasil"
license: "CC-BY-4.0"
editors:
  - "Equipe Oratio"
```

## Métricas geradas

Ao exportar uma anotação, o comando calcula métricas a partir da transcrição:

- `duration_seconds`: diferença entre o início do primeiro segmento e o final do último segmento com timestamps numéricos.
- `segment_count`: quantidade total de segmentos.
- `utterances_per_participant`: contagem de falas por participante (utilizando o nome canônico definido nos metadados).

Essas métricas ficam disponíveis no manifesto (`--manifest`) em um campo `metrics` para consumo posterior.
