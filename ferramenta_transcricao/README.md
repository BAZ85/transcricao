# Ferramenta de Transcrição Automática de Aulas

Percorre recursivamente as pastas de um curso em vídeo, extrai o áudio de cada `.mp4`,
transcreve localmente e corrige os termos técnicos da transcrição via API da OpenAI —
identificando sozinha, pelo conteúdo, qual é a disciplina tratada (direito tributário,
direito ambiental, medicina, engenharia etc.), sem precisar que isso seja informado.
O resultado é um `.md` com timestamps, salvo ao lado de cada vídeo.

## Como funciona

Para cada vídeo `.mp4` pendente, o pipeline roda em três etapas sequenciais
([`orquestrador.py`](orquestrador.py)):

1. **Extração de áudio** ([`extrator_audio.py`](extrator_audio.py)) — usa `ffmpeg` para
   extrair a faixa de áudio do vídeo para um `.mp3` na mesma pasta.
2. **Transcrição local** ([`transcritor_local.py`](transcritor_local.py)) — invoca o
   [`transcript-skill`](#transcript-skill) (`faster-whisper` rodando localmente, sem enviar
   áudio para nenhuma API externa) para gerar um `.srt` com timestamps. O processo é
   monitorado: se o `.srt` ficar muito tempo sem receber novos trechos, a transcrição é
   abortada (evita travar indefinidamente num vídeo problemático). Também detecta quando a
   transcrição para antes do fim real do áudio (um comportamento observado em áudios longos)
   e retranscreve automaticamente o trecho final que faltou.
3. **Correção de termos técnicos** ([`corretor_termos.py`](corretor_termos.py)) — envia os
   trechos transcritos, em lotes, para a API da OpenAI, que identifica a disciplina pelo
   próprio conteúdo e corrige apenas termos técnicos, siglas e jargão que o motor de
   transcrição de voz possa ter errado — sem resumir, sem reescrever estilo, sem alterar o
   restante do texto. Se a API falhar por qualquer motivo (chave ausente, rede,
   indisponibilidade, rate limit), a ferramenta não trava: cai em modo de fallback e salva a
   transcrição bruta mesmo assim, sinalizando o vídeo como "processado com aviso".

O texto final é salvo em blocos `**(HH:MM:SS -> HH:MM:SS)** texto`, um por trecho.

## Pré-requisitos

1. **`ffmpeg`** e **`ffprobe`** instalados e disponíveis no `PATH`.
2. **Python 3.10+** (o código usa sintaxe de union type `X | None`, introduzida no 3.10).
3. **[`transcript-skill`](#transcript-skill)** instalada e com suas próprias dependências
   resolvidas — veja abaixo.
4. Uma **chave de API da OpenAI**, usada só na etapa de correção de termos (a transcrição em
   si é 100% local).

### transcript-skill

A transcrição em si não é feita por este repositório: ele invoca um script externo,
`transcript-skill`, que roda o [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)
localmente (CPU ou GPU, se houver placa NVIDIA disponível). O caminho para esse script está
hardcoded em [`config.py`](config.py):

```python
TRANSCRIPT_SKILL_SCRIPT = Path(r"C:\pythonprojects\skills\transcript-skill\scripts\transcribe.py")
TRANSCRIPT_MODEL_SIZE = "small"
```

Ajuste `TRANSCRIPT_SKILL_SCRIPT` para o caminho real do script `transcribe.py` na sua
máquina. Na primeira execução, o próprio script instala a dependência `faster-whisper` (via
`pip`, no interpretador Python que estiver no `PATH`) e baixa o modelo do Hugging Face — é
necessário acesso à internet nesse primeiro uso, mesmo a transcrição em si sendo local.

`TRANSCRIPT_MODEL_SIZE` aceita os tamanhos de modelo do Whisper (`tiny`, `base`, `small`,
`medium`, `large`, ...) — quanto maior, melhor a qualidade e mais RAM/tempo de CPU consome.
Veja [Solução de problemas](#solução-de-problemas) se a transcrição travar no modelo
`small`.

## Instalação

```
pip install -r ferramenta_transcricao/requirements.txt
```

Crie um arquivo `.env` na raiz do projeto com a chave de API da OpenAI (use
`.env.example` como referência — nunca versione o `.env`):

```
OPENAI_API_KEY=sk-...
```

Opcionalmente, `config.py` também expõe `OPENAI_MODEL` (modelo usado na correção de termos)
e `PROGRESS_TIMEOUT_SECONDS` (tempo sem progresso na transcrição até abortar, padrão 10
minutos).

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

> Evite apontar o diretório raiz para dentro deste próprio repositório: os `.mp4`/`.mp3`/
> `.srt` gerados são ignorados pelo git (veja `.gitignore`), mas os `.md` de transcrição não
> têm como ser distinguidos automaticamente de documentação real do projeto.

## Controle de progresso

Rodar o comando de novo sobre o mesmo diretório não reprocessa vídeos que já têm `.mp3` e
`.md` correspondentes — só os vídeos novos são processados. Isso permite rodar a ferramenta
sempre que novas aulas forem adicionadas ao curso.

## Comportamento em caso de falha

- Falha em um vídeo específico (ex.: arquivo corrompido, timeout de transcrição sem
  progresso) não interrompe o processamento dos demais vídeos do lote — é registrada e
  reportada no resumo final.
- Falha na chamada à API da OpenAI (chave ausente, indisponibilidade, rate limit) não
  bloqueia a geração do `.md`: o arquivo é salvo com o texto bruto da transcrição, sem
  correção de termos, e o vídeo aparece no resumo como "processado com aviso".

## Solução de problemas

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
