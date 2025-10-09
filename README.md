# Oratio Transcripta

Pipeline em Python para **transcrição e anotação** automática de áudio, integrando Whisper, pyannote e outras ferramentas open-source para converter fala em texto e estruturar metadados de forma eficiente.

---

## Sobre o projeto

**Oratio Transcripta** é um projeto open-source para transcrição e anotação de dados de fala em suportes audiovisuais, transformando-os em texto estruturado. Inspirado na tradição clássica do termo *oratio* ("discurso") e no verbo latino *transcribere* ("passar de uma forma a outra"), o projeto une rigor e tecnologia para oferecer transcrições automáticas precisas e anotadas.

Construído em Python, integra ferramentas como Whisper, Faster-Whisper, WhisperX, pyannote.audio, Silero VAD e WebRTC VAD para formar um pipeline flexível de processamento de áudio. Entre suas capacidades estão:

- Converter fala em texto com alta fidelidade.
- Segmentar, anotar e estruturar metadados de forma clara.
- Apoiar aplicações em pesquisa, ensino, acessibilidade e arquivamento digital.

O **Oratio Transcripta** é uma proposta de valorização da palavra, da história e da memória.

---

## Visão geral da pipeline

O pipeline é dividido em dois estágios complementares:

1. **Estágio A – Transcrição automática (`python -m oratiotranscripta`)**
   - Ingestão e normalização do áudio (`ffmpeg`, 16 kHz mono por padrão).
   - Detecção de atividade de voz (VAD) com backends configuráveis.
   - Reconhecimento automático de fala (ASR) com Whisper ou Faster-Whisper.
   - (Opcional) Alinhamento com WhisperX para timestamps de palavras.
   - (Opcional) Diarização básica ou com modelos pyannote.
   - Agregação opcional em janelas temporais fixas.
   - Exportação para múltiplos formatos e geração de manifesto FAIR.

2. **Estágio B – Anotação de transcrições revisadas (`python -m oratiotranscripta.annotate`)**
   - Normalização de transcrições revisadas (TXT, SRT, VTT, JSON ou JSONL).
   - Associação com metadados de participantes/evento.
   - Reconciliação com segmentos brutos do Estágio A.
   - Exportação em JSON/JSONL e geração de manifesto FAIR + metadata normalizado.

Cada estágio pode ser usado de forma independente, mas foram concebidos para formar um fluxo contínuo de processamento → revisão → anotação.

---

## Recursos principais

- **Ingestão flexível**: suporte a arquivos locais ou YouTube (`yt-dlp`) com normalização automática de áudio via `ffmpeg`. Parâmetros como taxa de amostragem (16 kHz) e canais (mono) são padronizados pelo módulo de ingestão.
- **Detecção de voz (VAD)**: backends selecionáveis (`auto`, `webrtc`, `silero`, `pyannote`, `none`).
  - O backend Silero é carregado via `torch.hub` com `trust_repo=True` quando suportado.
  - O backend pyannote aceita tokens via `--pyannote-token` ou variáveis `HUGGINGFACE_TOKEN` / `PYANNOTE_TOKEN`.
- **Reconhecimento de fala (ASR)**: escolha entre Whisper oficial ou Faster-Whisper (CTranslate2) com seleção automática de CPU/GPU (`--device` também pode ser informado manualmente).
- **Alinhamento opcional**: integração com WhisperX para produzir timestamps de palavras de alta precisão.
- **Diarização**: heurísticas básicas de energia/pausa (`basic`) ou pipeline pré-treinado do `pyannote.audio` (requer token HF).
- **Agregação flexível**: preserva segmentos originais ou gera blocos temporais fixos (`--window`) adequados para legendas.
- **Exportação**: gera `.txt`, `.srt`, `.vtt` e `.json` com metadados de locutores, confiança e timestamps.
  - Cada execução cria um diretório isolado `output/<run_id>/` contendo os arquivos solicitados, além de `transcript.raw.json` com os segmentos originais antes da agregação.
  - Flags opcionais permitem exportar metadados detalhados em JSONL: `--export-json-raw` grava `transcript.raw_segments.jsonl` e `--export-json-words` registra `transcript.raw_words.jsonl` (quando timestamps de palavras estiverem disponíveis).
  - O campo `metadata` dos JSONs agrega informações sobre a execução (`pipeline`), artefatos de ingestão (`ingestion`) e versão do software (`software`).
  - Use `--manifest` para gerar `run_manifest.json` com proveniência (configurações, hashes de arquivos, ambiente e commit Git) e acesse os logs em `logs/pipeline.log`.

---

## Estrutura de saída (Estágio A)

```
output/<run_id>/
  ├─ transcript.txt/.srt/.vtt/.json   # formatos escolhidos em --export
  ├─ transcript.raw.json              # transcrição bruta (pré-agregação)
  ├─ transcript.raw_segments.jsonl    # opcional (--export-json-raw)
  ├─ transcript.raw_words.jsonl       # opcional (--export-json-words)
  ├─ run_manifest.json                # opcional (--manifest)
  └─ logs/pipeline.log                # log estruturado da execução
```

O nome-base `transcript` é derivado do argumento `--out`. Informe um `--run-id` para controlar o identificador do processamento ou deixe o padrão (timestamp UTC).

---

## Perfis de uso recomendados

| Tarefa | Modelo recomendado | Justificativa técnica e de uso |
| --- | --- | --- |
| 1. Transcrição de palestras/aulas com múltiplos interlocutores | **Pyannote** | Melhor diarização consistente e coesão semântica. Ideal para mesas, podcasts, discussões acadêmicas. |
| 2. Legendas sincronizadas em vídeos | **WebRTC** | Alta precisão temporal e sensibilidade a pausas curtas; excelente para `.srt/.vtt`. |
| 3. Gravações monofônicas em ambientes controlados | **Silero** | Leve e eficiente; indicado para entrevistas individuais/aulas. Roda bem sem GPU. |

Esses três modos formam o núcleo de um protocolo aberto de transcrição e anotação automática de fala, permitindo equilibrar precisão, desempenho e finalidade de pesquisa.

---

## Requisitos

- Python ≥ 3.10.
- `ffmpeg` disponível no `PATH` para normalização e extração de áudio.
- (Opcional) GPU CUDA para modelos Whisper/Faster-Whisper de maior porte.
- (Opcional) Token da Hugging Face (`--pyannote-token` ou variáveis de ambiente) para recursos pyannote.
- (Opcional) `PyYAML` para consumir arquivos de metadados YAML no Estágio B.

---

## Instalação

```bash
pip install .[all]  # instala o pacote e todas as dependências opcionais
```

Extras disponíveis (instale apenas o necessário):

| Extra | Dependências principais | Quando usar |
| --- | --- | --- |
| `asr` | `openai-whisper>=20230314` | Transcrição com Whisper oficial |
| `faster` | `faster-whisper>=0.9.0` | Transcrição com Faster-Whisper (CTranslate2) |
| `alignment` | `whisperx>=3.1` | Alinhamento de palavras com WhisperX |
| `diarization` | `pyannote.audio>=3.3`, `speechbrain>=1.0.0`, `matplotlib>=3.10,<3.11` | Pipeline pyannote para diarização/VAD |
| `pyannote` | `pyannote.audio>=3.3`, `speechbrain>=1.0.0`, `matplotlib>=3.10,<3.11` | Instalação dedicada às funcionalidades pyannote |
| `silero` | `torch>=2.0.0`, `torchaudio>=2.0.0` | VAD com Silero |
| `all` | União dos extras acima | Instalação completa |

Para instalações mínimas escolha apenas os extras necessários, por exemplo `pip install .[asr]` ou `pip install .[pyannote]`.

---

## Uso via CLI – Estágio A

Execute `python -m oratiotranscripta --help` para ver todas as opções.

| Opção | Descrição |
| --- | --- |
| `--source {local,youtube}` | Define a origem do áudio (default: `local`). |
| `--path PATH` | Caminho para arquivo local quando `--source=local`. |
| `--url URL` | URL do vídeo quando `--source=youtube`. |
| `--out PATH` | Caminho base dos arquivos de saída (padrão: `output`). Pode incluir nome-base. |
| `--run-id ID` | Define o identificador do processamento (timestamp UTC por padrão). |
| `--model NAME` | Modelo Whisper/Faster-Whisper a ser utilizado. |
| `--engine {whisper,faster-whisper}` | Backend de ASR. |
| `--device DEVICE` | Força o dispositivo (ex.: `cuda`, `cuda:1`, `cpu`). Caso ausente, a detecção é automática. |
| `--lang CODE` | Força idioma específico para a transcrição. |
| `--cookies PATH` | Arquivo de cookies (yt-dlp). |
| `--export ...` | Formatos de exportação (`txt`, `srt`, `vtt`, `json`). |
| `--window SEC` | Gera janelas fixas para legendas. Sem valor, mantém segmentos originais. |
| `--vad BACKEND` | Backend de VAD (`auto`, `webrtc`, `silero`, `pyannote`, `none`). |
| `--diarize {none,basic,pyannote}` | Método de diarização. |
| `--pyannote-token TOKEN` | Token HF usado em VAD/Diarização pyannote (alternativamente use variáveis de ambiente). |
| `--align` | Habilita alinhamento de palavras com WhisperX. |
| `--words` | Solicita metadados de palavras quando suportado pelo modelo ASR. |
| `--export-json-raw` | Exporta segmentos brutos pré-agregação em JSONL. |
| `--export-json-words` | Exporta palavras reconhecidas em JSONL (quando disponíveis). |
| `--manifest` | Gera `run_manifest.json` com proveniência, hashes e ambiente. |
| `--keep-temp` | Mantém diretórios temporários gerados na ingestão. |
| `--verbose` | Ativa logs detalhados (stdout e `logs/pipeline.log`). |

### Exemplos

Transcrever arquivo local com Whisper base, gerar SRT/JSON, diarização básica e janelas de 30 s:

```bash
python -m oratiotranscripta \
  --source local \
  --path ./audio.wav \
  --model base \
  --engine whisper \
  --export srt json \
  --diarize basic \
  --window 30 \
  --export-json-raw \
  --manifest
```

Baixar do YouTube com Faster-Whisper em GPU e VAD Silero:

```bash
python -m oratiotranscripta \
  --source youtube \
  --url https://youtu.be/xxxx \
  --engine faster-whisper \
  --model medium \
  --device cuda \
  --vad silero \
  --export txt vtt \
  --words \
  --export-json-words \
  --manifest
```

> **Dica:** use `--keep-temp` para inspecionar os arquivos intermediários no diretório de trabalho temporário.

---

## Uso via CLI – Estágio B

Após revisar manualmente um arquivo exportado pelo Estágio A, utilize `python -m oratiotranscripta.annotate` para gerar artefatos anotados. A ferramenta aceita `.txt`, `.srt`, `.vtt`, `.json` e `.jsonl`.

| Opção | Descrição |
| --- | --- |
| `--transcript PATH` | Arquivo revisado (obrigatório). |
| `--format auto|txt|srt|vtt|json|jsonl` | Controle manual do formato (padrão: `auto`). |
| `--metadata PATH` | Metadados adicionais (JSON ou YAML). Estrutura mínima: projeto, evento, participantes, datas, licença etc. |
| `--raw-json PATH` | Transcrição bruta exportada no Estágio A (`transcript.raw.json` ou `transcript.raw_segments.jsonl`). Mantém vínculos com segmentos originais. |
| `--export-format json|jsonl` | Formato de saída (padrão: `jsonl`). |
| `--out PATH` | Caminho do arquivo anotado (padrão: `stdout`). |
| `--manifest [PATH]` | Gera manifesto FAIR. Sem `PATH`, o destino é derivado de `--out` ou `--transcript`. |
| `--verbose` | Logs detalhados. |

### Metadados

Quando fornecido, o arquivo de metadados deve conter ao menos:

```yaml
project: Corpus Oralidade
event: Entrevista com participantes X e Y
participants:
  - name: Participante X
    role: entrevistado
  - name: Participante Y
    role: entrevistador
  - name: Revisora Z
    role: revisora
    aliases: ["Revisora", "Z"]
dates: ["2023-08-14"]
coverage:
  location: São Paulo
license: CC-BY-4.0
editors: ["Nome da editora"]
```

Aliases permitem reconciliar nomes diferentes que apareçam na transcrição. O comando valida automaticamente se todos os `speakers` presentes no arquivo revisado estão cadastrados.

### Exemplo

```bash
python -m oratiotranscripta.annotate \
  --transcript ./edited/entrevista.srt \
  --format auto \
  --metadata ./edited/entrevista.yml \
  --raw-json ./output/20240101T120000Z/transcript.raw.json \
  --export-format jsonl \
  --out ./edited/entrevista.annotated.jsonl \
  --manifest
```

O comando acima gera `entrevista.annotated.jsonl` e, automaticamente, `entrevista.annotated.manifest.json` (além de `metadata.yml/json`, se necessário). O manifesto inclui hashes, métricas básicas (número de segmentos, duração, falas por participante) e referências aos insumos utilizados.

---

## FAIR & Proveniência

- **Findable**: `run_manifest.json` (Estágio A) e `*.manifest.json` (Estágio B) listam arquivos, configuram hashes SHA256 e documentam parâmetros.
- **Accessible**: formatos abertos (`json`, `jsonl`, `txt`, `srt`, `vtt`) + logs legíveis.
- **Interoperable**: esquemas estáveis (`transcript.raw.json`, `raw_segments.jsonl`) e normalização de metadados com `DatasetMetadata`.
- **Reusable**: manifests incluem versão do software, configurações de pipeline, proveniência de ingestão e licenças declaradas.

---

## Limitações conhecidas

- Exportação TEI/XML está disponível apenas via API Python (`oratiotranscripta.annotate.tei`).
- Métricas avançadas e visualizações exploratórias não são geradas pela CLI (utilize notebooks/scripts dedicados).
- Alguns backends não expõem `confidence` por palavra/segmento — nesses casos o campo pode estar ausente nos JSONs.

---

## Desenvolvimento

- Submódulos principais: `ingest`, `vad`, `asr`, `alignment`, `diarization`, `aggregation`, `export`, `annotate` e `provenance`.
- Dependências pesadas são opcionais e só precisam ser instaladas quando o recurso correspondente for utilizado.
- Scripts CLI podem ser executados via `python -m oratiotranscripta` ou com o entry-point instalado `oratiotranscripta`.

Sinta-se à vontade para abrir issues ou PRs com melhorias e integrações adicionais.
