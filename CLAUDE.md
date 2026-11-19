# Dashamp

Dashamp é um projeto aberto (GitHub público, licença MIT) que transforma um Linux antigo
com tela num player de música compatível com skins clássicas `.wsz`, depois num motor de
mostradores (painel de instrumentos) e por fim num carputer com telemetria OBD-II.
A máquina de referência é um ASUS Eee PC 701; se rodar bem nela, roda em qualquer coisa.
O passo a passo está em `PLANO.md`. Siga-o na ordem.

## Repositório público

- **Nunca use a marca "Winamp"** em nomes de módulos, telas, logos ou no nome do app.
  Na documentação, descreva como "compatível com skins clássicas do Winamp 2 (.wsz)".
- **Nunca commite skins de terceiros** (`.wsz`, inclusive a padrão do Winamp) nem assets
  copiados de outros projetos. Skins de teste ficam em `player/skins_teste/` (no `.gitignore`)
  e são baixadas por `scripts/baixar_skins.sh`. Os temas de mostrador do projeto são gerados
  por código e podem ser commitados.
- **Nada pessoal no repositório**: IP, usuário, SSID, tokens e endereço do servidor ficam
  no `.env` (no `.gitignore`); o `.env.exemplo` lista as variáveis com valores fictícios.
- README em português e inglês. Antes de cada push, rode `git status` e confira que nada
  de `.env`, `tmp/` ou skins entrou no commit.

## Máquinas

| Papel | Máquina | Como acessar |
| --- | --- | --- |
| Desenvolvimento | PC de desenvolvimento (onde o Claude Code roda) | local |
| Alvo | ASUS Eee PC 701 4G | `ssh eeepc` |
| Servidor (fase 3) | qualquer host com Docker | definido pelo mantenedor |

Hardware do alvo — trate como restrição dura, não como sugestão:

- CPU Intel Celeron M 353 ULV, 900 MHz, **32 bits, um núcleo, sem PAE**.
- RAM: 512 MB ou 1 GB (valor real anotado em `docs/estado.md` após a F0).
- Armazenamento: flash interno de 4 GB, lento e com vida útil limitada.
- Tela 800×480. Saída de áudio P2. Rede: Ethernet 100 Mbit e Wi-Fi b/g.
- Sistema: Debian 12 i386, sem ambiente de desktop.

## Regras de trabalho

1. **Uma tarefa por vez**, na ordem de `PLANO.md`. Ao concluir uma tarefa, marque `[x]`
   no plano, atualize `docs/estado.md` e faça um commit com o ID da tarefa
   (ex.: `F1.3: leitor de .wsz`).
2. **Toda tarefa termina com verificação no Eee PC**, nunca só no PC. Os critérios de
   aceite de cada tarefa dizem o que medir.
3. **Tarefas marcadas `[HUMANO]`** precisam do mantenedor (algo físico, um teste no carro,
   uma olhada na tela). Pare, explique em poucas linhas o que ele precisa fazer e espere.
4. **Orçamento de recursos no Eee PC** (medir sempre que a tarefa mexer em desempenho):
   - app gráfico: ≥ 30 fps a 800×480, CPU ≤ 70%, memória (RSS) ≤ 150 MB;
   - nada de navegador, Electron, Node.js, Docker ou banco de dados servidor no Eee PC;
   - instale pacotes pelo `apt` sempre que existirem; `pip` só dentro do venv do projeto;
   - antes de instalar algo grande (> 50 MB), pergunte.
5. **Proteja o flash**: nada de logs verbosos gravando em disco o tempo todo; use o
   journald com limite (F0.6); arquivos temporários em `/tmp` (tmpfs).
6. **Comandos destrutivos no Eee PC** (formatar, apagar fora de `~/dashamp`, mexer em
   partições, desativar o SSH ou mudar a configuração de rede) só com confirmação explícita.
   Uma configuração errada de rede ou SSH tranca você para fora da máquina.
7. Nunca commitar segredos (token do servidor, senha do Wi-Fi). Use `.env`, que está no `.gitignore` (ver "Repositório público").

## Ciclo de desenvolvimento

```
editar no PC  →  ./deploy/deploy.sh  →  testar no Eee PC  →  ver captura de tela  →  commit
```

- `deploy/deploy.sh`: `rsync` (ou `tar` pelo SSH, no Git Bash) do repositório para `eeepc:~/dashamp`
  (sem `.git`, `.venv`, `__pycache__`) e reinício do app
  (`ssh eeepc 'pkill -f "[/]dashamp/.venv/bin/python -m" || true'`; o laço do `.xinitrc` o abre
  de novo). O app aberto no boot é escolhido em `~/dashamp/.app` (ver `deploy/run.sh`).
- O app roda no X do próprio Eee PC (`DISPLAY=:0`). Para rodar um teste avulso:
  `ssh eeepc 'cd ~/dashamp && DISPLAY=:0 .venv/bin/python -m <módulo>'`.
- **Para enxergar a tela**: todo app aceita `--captura <segundos>`. Ele salva um PNG em
  `/tmp/captura.png` depois desse tempo. Traga o arquivo com
  `scp eeepc:/tmp/captura.png ./tmp/` e abra-o para conferir o visual.
- **Para medir desempenho**: o app imprime fps, CPU e memória a cada 5 s quando recebe
  `--metricas`. Para uma medição pontual: `ssh eeepc 'top -b -n1 | head -15; free -m'`.
- Também é possível rodar o app no PC durante o desenvolvimento (janela de 800×480),
  mas o aceite vale sempre no Eee PC.

## Pilha técnica

- Python 3.11 (do Debian 12) com venv em `~/dashamp/.venv`.
- Gráficos: **pygame-ce** (SDL2) direto no X, sem gerenciador de janelas.
  Se não houver wheel i386, use o `python3-pygame` do apt (venv com
  `--system-site-packages`) e registre a decisão em `docs/estado.md`.
- Áudio: **GStreamer** via PyGObject (`playbin` + elemento `spectrum`).
- OBD: **python-OBD** (modo assíncrono); para testes sem carro, **ELM327-emulator**.
- Armazenamento local: SQLite.
- Servidor: FastAPI + PostgreSQL, empacotado em Docker.

## Estrutura

```
dashamp/
  CLAUDE.md
  PLANO.md
  README.md        # português e inglês
  LICENSE          # MIT
  .env.exemplo
  scripts/         # baixar_skins.sh e utilitários
  docs/estado.md   # estado atual, medições, decisões tomadas pelo caminho
  core/            # janela, laço de 30 fps, atlas de sprites, skins, fonte bitmap, métricas, captura
  player/          # leitor .wsz, áudio GStreamer, telas do player (skins_teste/ ignorada)
  painel/          # interface Fonte, widgets, temas
    fontes/        # simulada.py, replay.py, udp_f1.py, gt7.py, obd.py
    temas/         # vintage/, digital80/, moderno/
  carputer/        # agendador de PIDs, gravação SQLite, sincronização
  deploy/          # deploy.sh, run.sh, units systemd, configs do sistema
  servidor/        # API FastAPI e painel de viagens
  testes/          # pytest; roda no PC e no Eee PC
  tmp/             # capturas de tela trazidas do Eee PC (no .gitignore)
```

## Estilo de código

- Código, comentários e mensagens de commit em português; nomes de módulos sem acento.
- Type hints e funções pequenas. Nada de dependência nova sem justificativa em `docs/estado.md`.
- Desempenho primeiro: pré-renderizar o que for estático, redesenhar só o que muda,
  evitar alocação dentro do laço de quadro.
