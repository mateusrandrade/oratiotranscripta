# oratiotranscripta

Pipeline em Python para transcrição e anotação automática de áudio, integrando Whisper, pyannote e outras ferramentas open-source para converter fala em texto e estruturar metadados de forma eficiente.

## Sobre o projeto

### Oratio Transcripta

**Oratio Transcripta** é um projeto open-source para transcrição e anotação de dados de fala em suportes audiovisuais, transformando-os em texto estruturado. Inspirado na tradição clássica do termo *oratio* (“discurso”) e no verbo latino *transcribere* (“passar de uma forma a outra”), o projeto une rigor e tecnologia para oferecer transcrições automáticas precisas e anotadas.

Construído em Python, integra ferramentas como Whisper, pyannote e outras bibliotecas abertas para formar um pipeline flexível de processamento de áudio. Entre suas capacidades estão:

* Converter fala em texto com alta fidelidade.
* Segmentar, anotar e estruturar metadados de forma clara.
* Apoiar aplicações em pesquisa, ensino, acessibilidade e arquivamento digital.

O **Oratio Transcripta** é uma proposta de valorização da palavra, da história e da memória.

---

## Recursos principais

- **Ingestão flexível**: suporte a arquivos locais ou YouTube (`yt-dlp`) com normalização automática de áudio via `ffmpeg`.
- **Detecção de voz (VAD)**: backends selecionáveis (`webrtc`, `silero`, `pyannote`) com possibilidade de bypass.
  - O backend Silero é carregado via `torch.hub` com `trust_repo=True` para evitar prompts interativos sobre confiança no repositório oficial do modelo.
- **Reconhecimento de fala (ASR)**: escolha entre Whisper oficial ou Faster-Whisper (CTranslate2) com seleção automática de CPU/GPU.
- **Alinhamento opcional**: integração com WhisperX para produzir timestamps de palavras de alta precisão.
- **Diarização**: heurísticas básicas de energia/pausa ou pipeline pré-treinado do `pyannote.audio` (requer token HF).
- **Agregação flexível**: preserva segmentos originais ou gera blocos temporais fixos (`--window`) adequados para legendas.
- **Exportação rica**: gera `.txt`, `.srt`, `.vtt` e `.json` com metadados de speakers, confidences e timestamps.

## Instalação

```bash
pip install .[all]  # instala o pacote e todas as dependências opcionais
```

Para instalações mínimas use apenas o conjunto de extras necessário, por exemplo `pip install .[asr]`.

Certifique-se de ter `ffmpeg` disponível no PATH para normalização e extração de áudio.

## Uso via CLI

O módulo inclui um CLI baseado em `argparse`. Execute:

```bash
python -m oratiotranscripta --help
```

Opções principais:

| Opção | Descrição |
|-------|-----------|
| `--source {local,youtube}` | Define a origem do áudio (default: `local`). |
| `--path PATH` | Caminho para arquivo local quando `--source=local`. |
| `--url URL` | URL do vídeo quando `--source=youtube`. |
| `--out PATH` | Caminho base dos arquivos de saída (padrão: `output`). |
| `--model NAME` | Modelo Whisper/Faster-Whisper a ser utilizado. |
| `--engine {whisper,faster-whisper}` | Backend de ASR. |
| `--lang CODE` | Força idioma específico para a transcrição. |
| `--cookies PATH` | Arquivo de cookies (yt-dlp). |
| `--export ...` | Formatos de exportação (`txt`, `srt`, `vtt`, `json`). |
| `--window SEC` | Gera janelas fixas para legendas. |
| `--vad BACKEND` | Backend de VAD (`auto`, `webrtc`, `silero`, `pyannote`, `none`). |
| `--diarize {none,basic,pyannote}` | Método de diarização. |
| `--pyannote-token TOKEN` | Token HF usado em VAD/Diarização pyannote. |
| `--align` | Habilita alinhamento de palavras com WhisperX. |
| `--words` | Solicita metadados de palavras quando suportado pelo modelo ASR. |
| `--keep-temp` | Mantém diretórios temporários gerados. |
| `--verbose` | Ativa logs detalhados. |

### Exemplo

Transcrever arquivo local com Whisper base, gerar legendas em SRT e JSON, diarização básica e janelas de 30 segundos:

```bash
python -m oratiotranscripta \
  --source local \
  --path ./audio.wav \
  --model base \
  --engine whisper \
  --export srt json \
  --diarize basic \
  --window 30
```

Para baixar do YouTube com Faster-Whisper e VAD Silero:

```bash
python -m oratiotranscripta \
  --source youtube \
  --url https://youtu.be/xxxx \
  --engine faster-whisper \
  --model medium \
  --vad silero \
  --export txt vtt
```

## Desenvolvimento

- O pacote está organizado em submódulos (`ingest`, `vad`, `asr`, `alignment`, `diarization`, `aggregation`, `export`), permitindo substituições e extensões pontuais.
- Dependências pesadas são opcionais e só precisam ser instaladas quando o recurso correspondente for utilizado.
- Scripts CLI podem ser executados via `python -m oratiotranscripta` ou com o entry-point instalado `oratiotranscripta`.

Sinta-se à vontade para abrir issues ou PRs com melhorias e integrações adicionais.
