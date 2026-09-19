# Ferramenta de Transcrição Automática de Aulas

Percorre recursivamente as pastas de módulos de um curso em vídeo, extrai o áudio de cada
vídeo `.mp4`, transcreve localmente (via `transcript-skill`) e corrige termos técnicos via
API da OpenAI — a disciplina é identificada automaticamente a partir do próprio conteúdo
da transcrição, sem precisar ser informada —, salvando um `.md` de transcrição com
timestamps ao lado de cada vídeo.

## Pré-requisitos

1. `ffmpeg` instalado e disponível no `PATH`.
2. Python 3.8+.
3. [`transcript-skill`](C:\pythonprojects\skills\transcript-skill) instalada e com suas
   próprias dependências resolvidas.
4. Um arquivo `.env` na raiz do projeto com a chave de API da OpenAI:

   ```
   OPENAI_API_KEY=sk-...
   ```

   Use `.env.example` como referência. Nunca versione o `.env`.

## Instalação

```
pip install -r ferramenta_transcricao/requirements.txt
```

## Uso

```
python -m ferramenta_transcricao.cli "<diretorio_raiz_do_curso>"
```

O diretório informado deve conter as pastas de módulo com os vídeos `.mp4`. Ao final, cada
vídeo terá, na mesma pasta:

- `<nome>.mp3` — áudio extraído
- `<nome>.srt` — transcrição bruta com timestamps (arquivo intermediário)
- `<nome>.md` — transcrição final, com termos técnicos corrigidos e timestamps preservados
  no formato `**(HH:MM:SS -> HH:MM:SS)** texto`

## Controle de progresso

Rodar o comando de novo sobre o mesmo diretório não reprocessa vídeos que já têm `.mp3` e
`.md` correspondentes — só os vídeos novos são processados. Isso permite rodar a ferramenta
sempre que novas pastas de aulas forem adicionadas ao curso.

## Comportamento em caso de falha

- Falha em um vídeo (ex.: arquivo corrompido, timeout de transcrição após 10 minutos sem
  progresso) não interrompe o processamento dos demais vídeos do lote.
- Falha na chamada à API da OpenAI (chave ausente, indisponibilidade, rate limit) não
  bloqueia a geração do `.md`: o arquivo é salvo com o texto bruto da transcrição, sem
  correção, e o vídeo aparece no resumo final como "processado com aviso".

Ao final da execução, um resumo é impresso com o total de vídeos encontrados, processados,
processados com aviso, pulados e com falha.

Mais detalhes de teste em
[`_reversa_forward/001-transcricao-audio-videos/onboarding.md`](../_reversa_forward/001-transcricao-audio-videos/onboarding.md).
