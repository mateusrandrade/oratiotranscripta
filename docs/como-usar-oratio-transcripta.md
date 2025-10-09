# Como usar o Oratio Transcripta

Este guia mostra um exemplo de execução da CLI em um ambiente Windows PowerShell.

## Exemplo de transcrição a partir do YouTube

```powershell
python -m oratiotranscripta \
  --source youtube \
  --url https://youtu.be/SEU_VIDEO \
  --engine faster-whisper \
  --model medium \
  --device cuda \
  --vad silero \
  --out .\saidas\youtube \
  --run-id youtube_demo \
  --export txt vtt \
  --words \
  --manifest
```

O manifesto é salvo automaticamente como `<pasta_saida>/<run_id>/run_manifest.json`.

## Explicação das opções

| Opção | Explicação |
| --- | --- |
| `--source youtube` | Define o YouTube como origem do áudio. |
| `--url` | URL do vídeo a ser transcrito. |
| `--engine faster-whisper` | Seleciona o backend Faster-Whisper. |
| `--model medium` | Usa o modelo `medium` para a transcrição. |
| `--device cuda` | Executa na GPU com suporte CUDA. |
| `--vad silero` | Aplica detecção automática de voz com Silero. |
| `--out .\saidas\youtube` | Define a pasta base para os arquivos gerados. |
| `--run-id youtube_demo` | Define explicitamente o identificador da execução. |
| `--export txt vtt` | Exporta transcrições em TXT e VTT. |
| `--words` | Habilita exportação de timestamps por palavra. |
| `--manifest` | Gera `run_manifest.json` dentro da pasta da execução. |

## Resultado esperado

Após a execução, os arquivos ficam organizados em uma subpasta com o `run_id` dentro do diretório informado em `--out`:

```
.
└── saidas
    └── youtube
        └── <run_id>
            ├── run_manifest.json
            ├── youtube.raw_segments.jsonl
            ├── youtube.srt
            ├── youtube.txt
            └── youtube.vtt
```

Os nomes dos arquivos podem variar de acordo com as exportações solicitadas, mas os caminhos mantêm essa estrutura.

## Sessão 3 – Reprocessando uma transcrição existente

Você pode reutilizar os artefatos gerados anteriormente informando diretamente o JSON bruto e o manifesto:

```powershell
python -m oratiotranscripta \
  --raw-json .\saidas\youtube\<run_id>\youtube.raw_segments.jsonl \
  --manifest .\saidas\youtube\<run_id>\run_manifest.json
```

## Como localizar o `run_id`

Ao utilizar `--run-id`, você define manualmente o identificador que aparecerá como nome da subpasta. Caso essa opção não seja informada, o Oratio Transcripta gera automaticamente um `run_id` com base na data e hora da execução (por exemplo, `20240101-120000`). Nesse caso, consulte as subpastas dentro de `--out` para localizar o valor gerado ou defina o `run_id` manualmente para facilitar a organização dos resultados.
