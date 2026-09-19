# Ferramenta de Transcrição Automática de Aulas

Percorre recursivamente as pastas de um curso em vídeo, extrai o áudio de cada `.mp4`,
transcreve localmente e corrige os termos técnicos da transcrição via IA — à sua escolha,
OpenAI ou Anthropic Claude (e, por extensão, qualquer provedor com API compatível com a da
OpenAI, como DeepSeek, Qwen ou Grok — veja
[Usando outros modelos](#usando-outros-modelos-deepseek-qwen-grok-etc)) — identificando
sozinha, pelo conteúdo, qual é a disciplina tratada (direito tributário, direito ambiental,
medicina, engenharia etc.), sem precisar que isso seja informado. O resultado é um `.md`
com timestamps, salvo ao lado de cada vídeo.

## Início rápido

1. Instale o `ffmpeg` — veja [Instalando o ffmpeg](#instalando-o-ffmpeg).
2. `python verificar_ambiente.py` — instala as dependências e cria o `.env`.
3. No `.env` criado, defina `AI_PROVIDER` (`openai` ou `claude`) e preencha a
   chave de API correspondente — veja [Escolhendo o provedor de IA](#escolhendo-o-provedor-de-ia).
4. `python -m ferramenta_transcricao.cli "<diretorio_raiz_do_curso>"`

## Como funciona

Para cada vídeo `.mp4` pendente, o pipeline roda em três etapas sequenciais
([`orquestrador.py`](ferramenta_transcricao/orquestrador.py)):

1. **Extração de áudio** ([`extrator_audio.py`](ferramenta_transcricao/extrator_audio.py)) —
   usa `ffmpeg` para extrair a faixa de áudio do vídeo para um `.mp3` na mesma pasta.
2. **Transcrição local** ([`transcritor_local.py`](ferramenta_transcricao/transcritor_local.py))
   — invoca o script [`scripts/transcribe.py`](ferramenta_transcricao/scripts/transcribe.py),
   que roda o `faster-whisper` diretamente na sua máquina (CPU ou GPU, se houver placa
   NVIDIA disponível) para gerar um `.srt` com timestamps — o áudio nunca sai da máquina
   nessa etapa, nenhuma API externa é usada. O processo é monitorado: se o `.srt` ficar
   muito tempo sem receber novos trechos, a transcrição é abortada (evita travar
   indefinidamente num vídeo problemático). Também detecta quando a transcrição para antes
   do fim real do áudio (um comportamento observado em áudios longos) e retranscreve
   automaticamente o trecho final que faltou.
3. **Correção de termos técnicos**
   ([`corretor_termos.py`](ferramenta_transcricao/corretor_termos.py)) — envia os
   trechos transcritos, em lotes, para o provedor de IA escolhido em `AI_PROVIDER`
   (OpenAI ou Claude), que identifica a disciplina pelo próprio conteúdo e corrige
   apenas termos técnicos, siglas e jargão que o motor de transcrição de voz possa ter
   errado — sem resumir, sem reescrever estilo, sem alterar o restante do texto. Se a
   chamada falhar por qualquer motivo (chave ausente, rede, indisponibilidade, rate limit),
   a ferramenta não trava: cai em modo de fallback e salva a transcrição bruta mesmo assim,
   sinalizando o vídeo como "processado com aviso".

O texto final é salvo em blocos `**(HH:MM:SS -> HH:MM:SS)** texto`, um por trecho.

## Pré-requisitos

1. **`ffmpeg`** e **`ffprobe`** instalados e disponíveis no `PATH` — veja
   [Instalando o ffmpeg](#instalando-o-ffmpeg) abaixo. É o único requisito de sistema que
   precisa ser instalado manualmente.
2. **Python 3.10+** (o código usa sintaxe de union type `X | None`, introduzida no 3.10).
3. Uma **chave de API de um provedor de IA suportado** (OpenAI, Anthropic Claude, ou outro
   compatível com a API da OpenAI — veja
   [Escolhendo o provedor de IA](#escolhendo-o-provedor-de-ia)), usada só na etapa de
   correção de termos (a transcrição em si é 100% local — veja
   [Como funciona](#como-funciona)).

O motor de transcrição (`faster-whisper`) **não precisa ser instalado à parte**: o script
[`scripts/transcribe.py`](ferramenta_transcricao/scripts/transcribe.py) já vem dentro deste repositório e, na
primeira vez que rodar, instala sozinho a dependência `faster-whisper` via `pip` (no mesmo
interpretador Python usado para rodar o script) e baixa o modelo de reconhecimento de fala
do Hugging Face. É necessário acesso à internet só nesse primeiro uso — depois, o modelo
fica em cache local e tudo roda offline.

`TRANSCRIPT_MODEL_SIZE`, em [`config.py`](ferramenta_transcricao/config.py), aceita os tamanhos de modelo do
Whisper (`tiny`, `base`, `small`, `medium`, `large`, ...) — quanto maior, melhor a qualidade
e mais RAM/tempo de CPU consome. Veja [Solução de problemas](#solução-de-problemas) se a
transcrição travar no modelo `small`.

### Instalando o ffmpeg

**Windows:**
- Com [winget](https://learn.microsoft.com/windows/package-manager/winget/): `winget install ffmpeg`
- Ou com [Chocolatey](https://chocolatey.org/): `choco install ffmpeg`
- Ou manualmente: baixe o build em [ffmpeg.org/download.html](https://ffmpeg.org/download.html),
  extraia em uma pasta fixa (ex.: `C:\ffmpeg`) e adicione a subpasta `bin` (ex.:
  `C:\ffmpeg\bin`) à variável de ambiente `PATH` (Painel de Controle → Sistema →
  Configurações avançadas do sistema → Variáveis de Ambiente).

**macOS:** `brew install ffmpeg` (via [Homebrew](https://brew.sh/))

**Linux (Debian/Ubuntu):** `sudo apt install ffmpeg`

**Linux (Fedora):** `sudo dnf install ffmpeg`

Depois de instalar, confirme que está no `PATH` abrindo um novo terminal e rodando:

```
ffmpeg -version
ffprobe -version
```

Se qualquer um dos dois comandos não for reconhecido, o `PATH` não foi atualizado
corretamente (em geral, basta reabrir o terminal/IDE após a instalação).

### Escolhendo o provedor de IA

A etapa de correção de termos suporta dois provedores, escolhidos pela variável
`AI_PROVIDER` no `.env` — preencha só a chave do provedor escolhido:

| `AI_PROVIDER` | Chave de API        | Modelo (opcional, padrão em `config.py`) |
|---------------|---------------------|-------------------------------------------|
| `openai`      | `OPENAI_API_KEY`    | `OPENAI_MODEL`                             |
| `claude`      | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL`                          |

Os campos de modelo são opcionais: só precisam ser preenchidos se a conta usada não tiver
acesso ao modelo padrão definido em [`config.py`](ferramenta_transcricao/config.py). Trocar de provedor depois é
só mudar `AI_PROVIDER` e a chave correspondente no `.env` — nenhum código precisa mudar.


### Usando outros modelos (DeepSeek, Qwen, Grok, etc.)

Muitos provedores de IA expõem uma API compatível com a da OpenAI. Nesses casos não é
preciso nenhum código novo: use `AI_PROVIDER=openai` e aponte `OPENAI_BASE_URL` para o
endpoint do provedor, com `OPENAI_API_KEY` e `OPENAI_MODEL` preenchidos com a chave e o
nome do modelo daquele provedor. Exemplos (confirme o endpoint e o nome do modelo atuais na
documentação de cada provedor, pois mudam com o tempo):

| Provedor | `OPENAI_BASE_URL`                                  | `OPENAI_MODEL` (exemplo) |
|----------|-----------------------------------------------------|---------------------------|
| DeepSeek | `https://api.deepseek.com`                          | `deepseek-chat`           |
| Qwen (Alibaba, modo compatível) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Grok (xAI) | `https://api.x.ai/v1`                             | `grok-4`                  |
| Groq     | `https://api.groq.com/openai/v1`                    | (modelo hospedado no Groq) |
| Ollama (modelo local) | `http://localhost:11434/v1`            | (nome do modelo baixado localmente) |

Deixe `OPENAI_BASE_URL` em branco para usar a OpenAI oficial.

## Instalação

Depois de instalar o `ffmpeg` (acima), rode o script de setup na raiz do repositório:

```
python verificar_ambiente.py
```

Ele confere a versão do Python e a presença do `ffmpeg`/`ffprobe`, instala as dependências
de [`ferramenta_transcricao/requirements.txt`](ferramenta_transcricao/requirements.txt)
(incluindo os clientes dos provedores de IA suportados) e cria o `.env` a partir de
`.env.example` (se ainda não existir). Ao final, abra o `.env` criado e preencha
`AI_PROVIDER` e a chave de API correspondente — veja
[Escolhendo o provedor de IA](#escolhendo-o-provedor-de-ia).

`config.py` também expõe `PROGRESS_TIMEOUT_SECONDS` (tempo sem progresso na transcrição até
abortar, padrão 10 minutos).

Prefere fazer manualmente em vez de rodar o script? Basta `pip install -r
ferramenta_transcricao/requirements.txt` e copiar `.env.example` para `.env`.

## Uso

```
python -m ferramenta_transcricao.cli "<diretorio_raiz_do_curso>"
```

O diretório informado deve conter (em qualquer nível, a busca é recursiva) os vídeos
`.mp4` do curso. Ao final, cada vídeo tem, na mesma pasta:

- `<nome>.mp3` — áudio extraído
- `<nome>.srt` — transcrição bruta com timestamps (arquivo intermediário)
- `<nome>.md` — transcrição final, com termos técnicos corrigidos e timestamps preservados
  no formato `**(HH:MM:SS -> HH:MM:SS)** texto`

Ao final da execução, um resumo é impresso com o total de vídeos encontrados, processados,
processados com aviso, pulados e com falha.


## Controle de progresso

Rodar o comando de novo sobre o mesmo diretório não reprocessa vídeos que já têm `.mp3` e
`.md` correspondentes — só os vídeos novos são processados. Isso permite rodar a ferramenta
sempre que novas aulas forem adicionadas ao curso.

## Comportamento em caso de falha

- Falha em um vídeo específico (ex.: arquivo corrompido, timeout de transcrição sem
  progresso) não interrompe o processamento dos demais vídeos do lote — é registrada e
  reportada no resumo final.
- Falha na chamada ao provedor de IA escolhido (chave ausente, `AI_PROVIDER` inválido,
  indisponibilidade, rate limit) não bloqueia a geração do `.md`: o arquivo é salvo com o
  texto bruto da transcrição, sem correção de termos, e o vídeo aparece no resumo como
  "processado com aviso".

## Solução de problemas

**`ExtracaoAudioError` / "ffmpeg falhou" logo no início.** O `ffmpeg` não está instalado ou
não está no `PATH`. Veja [Instalando o ffmpeg](#instalando-o-ffmpeg).

**Falha ao instalar `faster-whisper` na primeira execução.** Precisa de internet nesse
primeiro uso (para o `pip install` e o download do modelo). Sem internet, essa etapa falha.

**A transcrição trava ou o processo morre no meio, sem erro no log.** Em máquinas com pouca
RAM livre, o modelo `small` do `faster-whisper` pode falhar de forma abrupta durante a
decodificação. Troque `TRANSCRIPT_MODEL_SIZE` em `config.py` para `"base"` — é mais leve e
tende a ser estável nessas condições, com alguma perda de qualidade na transcrição.

**Rode uma transcrição por vez.** Processar vários vídeos longos em paralelo (ex.: duas
instâncias da CLI ao mesmo tempo) aumenta a pressão de memória e a chance de falhas como a
descrita acima.

**Primeira execução demorada / baixando modelo.** É esperado: o `faster-whisper` baixa o
modelo do Hugging Face na primeira vez que é usado. Chamadas seguintes usam o modelo em
cache local.

## Licença

[MIT](LICENSE).
