# 🗣️ Como usar o Oratio Transcripta

Guia completo e didático para instalar, configurar e utilizar o **Oratio Transcripta** no Windows — mesmo que você **nunca tenha usado Python antes**.

---

## 📘 O que é o Oratio Transcripta?

**Oratio Transcripta** é uma pipeline em Python para **transcrição e anotação automática de áudio e vídeo**, integrando tecnologias abertas como **Whisper**, **Pyannote**, **WebRTC** e **Silero**.

Ela permite transformar gravações de entrevistas, aulas, palestras ou vídeos em **textos estruturados com metadados FAIR** — ou seja, **encontráveis, acessíveis, interoperáveis e reutilizáveis**.

---

## 🧩 Requisitos básicos

| Componente | Função | Onde obter |
|-------------|--------|-------------|
| **Windows 10 ou 11** | Sistema operacional | — |
| **Python 3.9 ou superior** (recomenda-se 3.10/3.11) | Linguagem usada pelo projeto | [python.org/downloads](https://www.python.org/downloads/) |
| **FFmpeg** | Processamento e normalização de áudio | [ffmpeg.org/download.html](https://ffmpeg.org/download.html) |
| **Visual Studio Build Tools (C++)** | Necessário apenas se `webrtcvad` precisar ser compilado | [visualstudio.microsoft.com/downloads](https://visualstudio.microsoft.com/downloads/) |
| **(Opcional) GPU NVIDIA** | Aceleração de processamento | Drivers atualizados |
| **(Opcional) Conta na Hugging Face** | Requerida para modelos `pyannote` | [huggingface.co](https://huggingface.co) |

> 💡 **Dica**: Alguns pacotes, como PyTorch, podem demorar a oferecer instaladores para versões muito novas do Python. Priorize 3.10 ou 3.11 para garantir compatibilidade com CUDA e aceleração via GPU.

---

## 🧱 Etapa 1 – Instalar o Python

### Opção A – Instalação automática (recomendada)
1. Abra o **PowerShell** (menu iniciar → digite `PowerShell`).
2. Execute o comando:

    ```powershell
    winget install Python.Python.3.12
    ```

3. Feche e abra novamente o PowerShell para que o PATH seja atualizado.
4. Verifique se o Python e o `pip` foram instalados corretamente:

    ```powershell
    python --version
    pip --version
    ```

    Saídas esperadas (exemplos):

    ```text
    Python 3.12.x
    pip 24.x.x
    ```

    > ✅ O Oratio Transcripta também funciona com Python 3.9, 3.10 e 3.11. Se já tiver uma dessas versões instaladas, o guia continua válido.

### Opção B – Instalação manual
1. Acesse [python.org/downloads](https://www.python.org/downloads/).
2. Baixe o instalador da versão LTS desejada (3.10 ou 3.11 são as mais compatíveis para bibliotecas de IA).
3. Durante a instalação, marque a caixa **“Add Python to PATH”**.
4. Conclua a instalação e repita o teste com `python --version` e `pip --version`.

---

## 🎵 Etapa 2 – Instalar o FFmpeg e adicionar ao PATH

### Opção A – Instalação automática
```powershell
winget install Gyan.FFmpeg
```

### Opção B – Instalação manual
1. Baixe o pacote ZIP **“ffmpeg-release-essentials”** para Windows.
2. Extraia o conteúdo em `C:\\ffmpeg\\` (o caminho pode ser outro, se preferir).
3. Adicione `C:\\ffmpeg\\bin` ao PATH do Windows:
   - Painel de Controle → Sistema → Configurações avançadas do sistema.
   - Clique em **Variáveis de Ambiente**.
   - Em **Variáveis do sistema**, selecione `Path` → **Editar** → **Novo** → `C:\\ffmpeg\\bin` → **OK**.
4. Feche e abra novamente o PowerShell e teste:

   ```powershell
   ffmpeg -version
   ```

   A exibição da versão confirma que está tudo certo ✅

---

## 🛠️ Etapa 3 – Preparar o ambiente de desenvolvimento

### 3.1 Baixar o código do projeto
1. Acesse o repositório oficial (por exemplo, no GitHub).
2. Clique em **Code → Download ZIP**.
3. Extraia o conteúdo em uma pasta fácil de lembrar, como `C:\\Projetos\\oratiotranscripta`.

> 💾 Se preferir usar Git, você pode executar `git clone https://github.com/...` no PowerShell. O restante das instruções permanece igual.

### 3.2 Criar um ambiente virtual (venv)
1. Abra o PowerShell e navegue até a pasta do projeto:

    ```powershell
    cd C:\\Projetos\\oratiotranscripta
    ```

2. Crie o ambiente virtual:

    ```powershell
    python -m venv .venv
    ```

3. Permita a execução de scripts na sessão atual (necessário para ativar o venv):

    ```powershell
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    ```

4. Ative o ambiente virtual:

    ```powershell
    .\\.venv\\Scripts\\Activate.ps1
    ```

    Você verá o prefixo `(.venv)` antes do prompt, indicando que o ambiente está ativo.

5. Atualize o `pip` dentro do venv:

    ```powershell
    python -m pip install --upgrade pip
    ```

### 3.3 Instalar dependências do projeto
```powershell
pip install -U ".[all]"
```

> ⚠️ Se ocorrer erro ao instalar `webrtcvad`, instale o **Visual Studio Build Tools** com a carga **Desktop development with C++** e repita o comando acima.

---

## 🔑 Etapa 4 – Criar e configurar sua conta na Hugging Face (para Pyannote)

1. Acesse [huggingface.co](https://huggingface.co) e crie uma conta gratuita.
2. Aceite os termos de uso dos modelos:
   - [`pyannote/voice-activity-detection`](https://huggingface.co/pyannote/voice-activity-detection)
   - [`pyannote/speaker-diarization-3.1`](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [`pyannote/segmentation-3.0`](https://huggingface.co/pyannote/segmentation-3.0)
3. Vá em **Settings → Access Tokens** e clique em **Create new token**:
   - Tipo: `Read`
   - Copie o token (ele começa com `hf_...`).

### Usando o token
- **Opção A – Informar diretamente na linha de comando** (válido apenas para aquela execução):

  ```powershell
  --pyannote-token hf_SEU_TOKEN_AQUI
  ```

- **Opção B – Salvar como variável de ambiente** (fica disponível em novas sessões):

  ```powershell
  setx HUGGINGFACE_TOKEN "hf_SEU_TOKEN_AQUI"
  setx PYANNOTE_TOKEN "hf_SEU_TOKEN_AQUI"
  ```

  Depois de executar, feche e abra o PowerShell novamente para que as variáveis sejam carregadas.

---

## 🎧 Etapa 5 – Testar o funcionamento da CLI

Com o ambiente virtual ativo (`(.venv)` no prompt), execute:

```powershell
python -m oratiotranscripta --help
python -m oratiotranscripta.annotate --help
```

A exibição das opções da CLI confirma que a instalação está pronta 🎉

---

## 🚀 Sessão 1 – Transcrever um vídeo do YouTube

Exemplo básico executado apenas na CPU (sem GPU). Ajuste os valores entre aspas conforme o seu caso.

```powershell
python -m oratiotranscripta \
  --source youtube \
  --url "https://www.youtube.com/watch?v=XXXXXXXXXXX" \
  --engine faster-whisper \
  --model medium \
  --lang pt \
  --vad webrtc \
  --diarize basic \
  --export txt srt vtt json \
  --export-json-raw \
  --out .\\saidas\\youtube \
  --run-id youtube_demo \
  --manifest
```

### Explicação das opções principais

| Flag | Função |
|------|--------|
| `--source youtube` | Informa que o áudio será baixado do YouTube. |
| `--url` | Link do vídeo a ser processado. |
| `--engine faster-whisper` | Transcrição otimizada (usa CTranslate2). |
| `--model medium` | Define o modelo de ASR (quanto maior, mais preciso e lento). |
| `--lang pt` | Força o idioma português. |
| `--vad webrtc` | Detecção de fala estável e eficiente em CPU. |
| `--diarize basic` | Separação simples de falantes. |
| `--export txt srt vtt json` | Gera múltiplos formatos de transcrição. |
| `--export-json-raw` | Gera o arquivo bruto `*.raw_segments.jsonl`. |
| `--out .\\saidas\\youtube` | Define a pasta base onde os resultados serão salvos. |
| `--run-id youtube_demo` | Define manualmente o identificador da execução (subpasta). |
| `--manifest` | Gera `run_manifest.json` automaticamente dentro da pasta da execução. |

> 🗂️ **Onde os arquivos são salvos?** Sempre é criada uma subpasta com o valor de `--run-id` (ou um timestamp automático). Dentro dela, os arquivos usam o nome da pasta de saída (`youtube` no exemplo) como prefixo.

### Resultado esperado

```text
.\\saidas\\youtube\\youtube_demo\\
├─ logs\\pipeline.log
├─ run_manifest.json
├─ youtube.json
├─ youtube.raw_segments.jsonl
├─ youtube.srt
├─ youtube.txt
└─ youtube.vtt
```

Se você não informar `--run-id`, o Oratio Transcripta criará algo como `20240101-120000`. O manifesto é salvo automaticamente como `<pasta_saida>/<run_id>/run_manifest.json`.

---

## 🧑‍💻 Sessão 2 – Transcrever um arquivo local

```powershell
python -m oratiotranscripta \
  --source local \
  --path "D:\\MeusAudios\\Aula1.mp3" \
  --engine faster-whisper \
  --model medium \
  --lang pt \
  --vad webrtc \
  --diarize basic \
  --export txt srt vtt \
  --out .\\saidas\\local \
  --run-id aula1 \
  --manifest
```

Para usar GPU (CUDA), acrescente `--device cuda`. Se quiser acelerar ainda mais, combine com `--compute-type float16`.

Resultado organizado em `.\\saidas\\local\\aula1\\`, com arquivos `local.txt`, `local.srt`, `local.vtt`, `local.raw_segments.jsonl` e `run_manifest.json`.

---

## 📝 Sessão 3 – Anotar uma transcrição revisada (Estágio B)

Após revisar manualmente o arquivo `.txt`, `.srt` ou `.vtt` gerado na etapa anterior, execute:

```powershell
python -m oratiotranscripta.annotate \
  --transcript .\\edited\\entrevista.srt \
  --format auto \
  --metadata .\\edited\\entrevista.yml \
  --raw-json .\\saidas\\youtube\\youtube_demo\\youtube.raw_segments.jsonl \
  --export-format jsonl \
  --out .\\publish\\entrevista.annotated.jsonl \
  --manifest
```

Esse comando:

- Gera um arquivo `.jsonl` anotado com IDs estáveis.
- Cria um manifesto FAIR (`entrevista.annotated.manifest.json`) com hashes, métricas e proveniência.
- Permite rastrear o caminho entre o áudio original e o texto revisado.

> 🔁 **Manifesto da anotação**: quando `--manifest` é utilizado na CLI de anotação, o arquivo é salvo ao lado da saída final, com sufixo `.manifest.json` (por exemplo, `entrevista.annotated.manifest.json`).

---

## ⚖️ Sessão 4 – Entendendo os estágios da pipeline

| Estágio | Função | Saídas principais |
|---------|--------|-------------------|
| **A – Transcrição** | Processa o áudio/vídeo, detecta falas, cria arquivos TXT/SRT/VTT, JSON e JSONL. | `*.txt`, `*.srt`, `*.vtt`, `*.json`, `*.raw_segments.jsonl`, `run_manifest.json` |
| **B – Anotação** | Integra revisão humana, gera dataset anotado e manifesto FAIR. | `*.annotated.jsonl`, `*.annotated.manifest.json` |

---

## 🧭 Como localizar ou definir o `run_id`

- **Definir manualmente**: use `--run-id nome_da_execucao` para criar uma subpasta previsível.
- **Gerado automaticamente**: se não informar a flag, o Oratio Transcripta cria um `run_id` com data e hora (`YYYYMMDD-HHMMSS`). Verifique as subpastas dentro do diretório definido em `--out` para descobrir o valor.
- **Reutilizar artefatos**: nos comandos que precisam de `--raw-json` ou `--manifest`, sempre inclua o caminho completo até essa subpasta, por exemplo: `.\\saidas\\youtube\\20240101-120000\\youtube.raw_segments.jsonl`.

---

## 🧭 Sessão 5 – Problemas comuns (troubleshooting)

| Erro ou situação | Solução |
|------------------|---------|
| “execução de scripts foi desabilitada” | Rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force` antes de ativar o venv. |
| `ffmpeg` não reconhecido | Reabra o PowerShell e confirme se `C:\\ffmpeg\\bin` (ou equivalente) está no PATH. |
| Falha na instalação de `webrtcvad` | Instale o Visual Studio Build Tools (Desktop development with C++) e repita `pip install -U ".[all]"`. |
| Erro 401/403 ao usar Pyannote | Aceite os termos dos modelos na Hugging Face e confirme se o token está correto. |
| Transcrição muito lenta em CPU | Use `--engine faster-whisper`, reduza o modelo (`small`, `base`) ou utilize uma GPU com `--device cuda`. |

---

## 💡 Dicas úteis

- Organize seus resultados em subpastas por projeto ou gravação.
- Guarde sempre os arquivos brutos (`*.raw_segments.jsonl`) e `run_manifest.json` — eles são a “assinatura digital” da execução.
- Para publicar resultados como dataset FAIR, inclua:
  - `metadata.yml`
  - `run_manifest.json`
  - `*.annotated.jsonl`
  - Licença (por exemplo, `LICENSE` ou `CC-BY-4.0.txt`)
- Se quiser acompanhar palavra a palavra, acrescente `--words --align` ao comando de transcrição (requer modelos compatíveis, como WhisperX).

---

## 📂 Estrutura típica de projeto

```text
oratiotranscripta/
│
├─ output/
│   └─ youtube_demo/
│       ├─ logs/
│       │   └─ pipeline.log
│       ├─ run_manifest.json
│       ├─ youtube.json
│       ├─ youtube.raw_segments.jsonl
│       ├─ youtube.srt
│       ├─ youtube.txt
│       └─ youtube.vtt
│
├─ edited/
│   ├─ entrevista.srt
│   └─ metadata.yml
│
└─ publish/
    ├─ entrevista.annotated.jsonl
    └─ entrevista.annotated.manifest.json
```

---

## 📖 Recursos avançados

- **Alinhamento palavra a palavra (WhisperX):** adicione `--align --words --export json` durante a transcrição.
- **Uso do Pyannote com token:** combine `--vad pyannote --diarize pyannote --pyannote-token hf_SEU_TOKEN` para diarização avançada.
- **Métricas e metadados automáticos:** os manifestos (`run_manifest.json` e `*.annotated.manifest.json`) incluem:
  - Hashes SHA256
  - Tempo total e número de falas
  - Modelos e versões utilizados
  - Caminhos relativos dos arquivos

---

## 🌐 Plataformas suportadas

| Sistema | Compatibilidade | Observações |
|---------|-----------------|-------------|
| **Windows 10/11** | ✅ Completo | Guia principal. |
| **macOS** | ✅ (CPU) | Instale via Homebrew: `brew install python ffmpeg`. |
| **Linux (Ubuntu/Debian)** | ✅ | `sudo apt install python3-venv ffmpeg git`. |

---

## 🏁 Pronto para começar!

Agora você pode:

- Transcrever entrevistas e vídeos;
- Revisar manualmente e gerar datasets anotados;
- Exportar metadados FAIR para reprodutibilidade completa;
- Compartilhar resultados de forma transparente, valorizando a palavra, a memória e a pesquisa.

O **Oratio Transcripta** vai além de uma ferramenta de transcrição — é uma proposta de ciência aberta aplicada à fala.
