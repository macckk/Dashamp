# Plano de trabalho — Dashamp

Execute as tarefas na ordem. Cada uma tem **Fazer** e **Aceite**. Só marque `[x]` quando
o aceite tiver sido verificado no Eee PC. Tarefas `[HUMANO]` esperam o mantenedor.
Regras gerais, ciclo de deploy e pilha técnica estão em `CLAUDE.md`.

---

## Fase 0 — Preparação do Eee PC

### [x] F0.0 `[HUMANO]` + Claude: repositório público
**Fazer:**
- Repositório público já criado: https://github.com/macckk/Dashamp. Pasta local: `F:\Dashamp`
  (Windows; os comandos de SSH e Git rodam no PowerShell ou no Git Bash).
- Claude cria o `.env.exemplo` (só valores fictícios) com as variáveis `DASHAMP_HOST_ALVO=eeepc`,
  `DASHAMP_SSID_CASA`, `DASHAMP_SERVIDOR_URL` e `DASHAMP_SERVIDOR_TOKEN`.
- Claude confere que `README.md`, `LICENSE`, `.gitignore`, `.env.exemplo`, `CLAUDE.md` e `PLANO.md`
  estão na raiz, faz `git init`, liga ao remoto `https://github.com/macckk/Dashamp.git`, faz o
  primeiro commit e o push para a branch `main`.
- Depois do push, conferir no GitHub que não há `.env`, IP, usuário ou skins publicados.

**Aceite:** o repositório público mostra o README bilíngue e a licença MIT.

### [x] F0.1 `[HUMANO]` Instalar o Debian 12 i386
Feito pelo mantenedor (pode ocorrer antes ou depois da F0.0):
- ISO **Debian 12 i386 netinst** (última 12.x) gravada num pendrive; Eee PC no cabo de rede.
- Hostname `eeepc`; usuário comum com senha; senha de root vazia (assim o usuário entra no grupo `sudo`).
- Particionamento: flash interno inteiro como `/` (ext4), **sem swap**.
- Seleção de software: só **SSH server** e **standard system utilities**.
- No roteador, reservar um IP fixo para o Eee PC.

**Aceite:** o mantenedor informa o IP e o usuário.

### [x] F0.2 Acesso SSH por chave
**Fazer:**
- Gerar uma chave dedicada no PC (`~/.ssh/eeepc_ed25519`) e copiá-la com `ssh-copy-id` (o mantenedor digita a senha uma vez).
- Adicionar ao `~/.ssh/config` do PC:
  ```
  Host eeepc
      HostName <IP>
      User <usuario>
      IdentityFile ~/.ssh/eeepc_ed25519
  ```
- Configurar `sudo` sem senha para o usuário (`/etc/sudoers.d/eeepc`, validar com `visudo -c`).
- **Só depois de confirmar que o login por chave funciona**, desativar o login por senha no `sshd`.

**Aceite:** `ssh eeepc 'sudo -n true && echo ok'` imprime `ok` sem pedir senha.

### [x] F0.3 Levantamento da máquina
**Fazer:** coletar `uname -a`, `free -m`, `df -h`, `lscpu`, `cat /proc/cpuinfo | grep flags`,
`lsblk`, `aplay -l`, `ip -br a`, `lsusb` e o kernel instalado (deve ser o `686`, sem `-pae`).
Criar `docs/estado.md` com o resumo.

**Aceite:** `docs/estado.md` informa a RAM real, o espaço livre e o kernel. Se a RAM for 512 MB,
anotar que o orçamento de memória do app cai para 120 MB.

### [x] F0.4 Pacotes base
**Fazer:** `apt install` de: `rsync xserver-xorg-core xserver-xorg-video-intel xinit x11-xserver-utils
python3-venv python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0
gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-alsa
alsa-utils unzip sqlite3 htop`. Sem `--install-recommends`.

**Aceite:** `startx` sobe no Eee PC (testar com `ssh eeepc 'xinit /usr/bin/xsetroot -solid gray -- :0 vt1 & sleep 5; pkill xinit'`)
e `speaker-test -c2 -l1` gera som. `df -h /` ainda mostra ≥ 1,5 GB livres.

### [x] F0.5 Repositório, venv e deploy
**Fazer:**
- Criar a estrutura de pastas de `CLAUDE.md` (o `.gitignore` e o repositório já existem desde a F0.0).
- No Eee PC: `python3 -m venv ~/dashamp/.venv` e tentar `pip install pygame-ce`. Se falhar,
  recriar o venv com `--system-site-packages`, usar o `python3-pygame` do apt e registrar em `docs/estado.md`.
- Escrever `deploy/deploy.sh` (rsync + reinício) e `deploy/requirements.txt`.

**Aceite:** `./deploy/deploy.sh` roda sem erro e `ssh eeepc '~/dashamp/.venv/bin/python -c "import pygame, gi; print(pygame.version.ver)"'` imprime a versão.

### [x] F0.6 Proteger o flash
**Fazer:** `noatime` no `/etc/fstab`; `/tmp` em tmpfs; journald com `Storage=volatile` e
`RuntimeMaxUse=16M`; desativar serviços desnecessários (listar com `systemctl list-unit-files --state=enabled`
e propor a lista antes de desativar).

**Aceite:** após `sudo reboot`, o SSH volta, `findmnt /tmp` mostra tmpfs e `mount | grep ' / '` mostra `noatime`.

### [x] F0.7 Núcleo mínimo: janela, métricas e captura
**Fazer:** em `core/`:
- `app.py`: janela 800×480 sem bordas, laço com limite de 30 fps, saída com Esc/Q.
- `metricas.py`: fps médio, CPU do processo e RSS (lidos de `/proc/self/stat` e `/proc/self/status`), impressos a cada 5 s com `--metricas`.
- `captura.py`: `--captura N` salva `/tmp/captura.png` após N segundos.

**Aceite:** no Eee PC, a janela abre, a captura é trazida ao PC e mostra o conteúdo esperado.

### [x] F0.8 Teste decisivo de desempenho
**Fazer:** `core/bench_ponteiro.py`: fundo de mostrador 400×400 pré-renderizado + ponteiro girando
com `pygame.transform.rotate` a cada quadro, mais um texto de fps. Medir três variações e registrar
em `docs/estado.md`: rotação a cada quadro; ângulos pré-renderizados (cache de 360 sprites); tela cheia
800×480 com dois mostradores.

**Aceite:** pelo menos uma variação com dois mostradores atinge ≥ 30 fps e CPU ≤ 70% no Eee PC.
Se nenhuma atingir, **pare e reporte os números**: o plano das fases 1–3 precisa ser revisto.

### [x] F0.9 Boot direto no app
**Fazer:**
- Autologin no tty1 (`/etc/systemd/system/getty@tty1.service.d/override.conf`).
- `~/.bash_profile`: se estiver no tty1, `exec startx`.
- `~/.xinitrc`: desativar descanso de tela (`xset s off -dpms`), esconder o cursor e rodar
  `deploy/run.sh` em laço (`while true; do ...; sleep 1; done`), de modo que o app reabra se fechar.
- `deploy/run.sh` abre o app escolhido em `~/dashamp/.app` (por enquanto, o bench).

**Aceite:** após `sudo reboot`, o Eee PC cai direto no bench sem intervenção.

### [x] F0.10 `[HUMANO]` Conferência visual
O mantenedor olha a tela real (brilho, nitidez, fluidez do ponteiro) e confirma.

---

## Fase 1 — Player com skins clássicas

### [ ] F1.1 Skins de teste
**Fazer:** `scripts/baixar_skins.sh` baixa 3 skins clássicas `.wsz` do Winamp Skin Museum para
`player/skins_teste/` (a padrão do Winamp 2 e duas bem diferentes), com as URLs listadas no próprio
script. A pasta está no `.gitignore`: as skins nunca vão para o repositório. Se o download for
bloqueado, pedir ao mantenedor.

**Aceite:** os três arquivos abrem com `unzip -l` e `git status` não os mostra.

### [ ] F1.2 Leitor de `.wsz`
**Fazer:** `core/skin.py`: abre o zip (nomes de arquivo sem diferenciar maiúsculas), carrega os BMPs
como superfícies pygame, lê `viscolor.txt` (24 cores) e `pledit.txt` (seção `[Text]`), com fallback
para a skin padrão quando faltar arquivo.

**Aceite:** testes em `testes/test_skin.py` passam no Eee PC para as três skins; tempo de carga < 1 s.

### [ ] F1.3 Mapa de sprites
**Fazer:** `player/sprites.py`: tabela de coordenadas de cada elemento (botões normal/pressionado,
dígitos, letreiro, barras de posição/volume/balanço, indicadores mono/estéreo, play/pause), usando o
código-fonte do Webamp como referência.

**Aceite:** um script de inspeção desenha todos os sprites rotulados numa grade; a captura confere
visualmente com a skin original.

### [ ] F1.4 Janela principal estática
**Fazer:** `player/janela_principal.py` desenha a janela de 275×116 (com escala 1× e 2×) usando a skin.

**Aceite:** a captura no Eee PC fica idêntica a uma referência do Winamp com a mesma skin.

### [ ] F1.5 Motor de áudio
**Fazer:** `player/audio.py`: `playbin` do GStreamer em uma thread com GLib MainLoop; play, pausa, stop,
busca, volume, balanço, posição e duração; elemento `spectrum` (bandas suficientes para 19 barras, ~20 Hz)
publicando magnitudes numa fila lida pelo laço do pygame.

**Aceite:** MP3 de 320 kbps toca sem falhas por 5 minutos; CPU total ≤ 50% só com áudio + espectro.

### [ ] F1.6 Player funcional
**Fazer:** ligar a interface ao áudio: tempo em dígitos, letreiro rolando com título/artista (tags),
kbps/kHz, barra de posição, analisador de barras com as cores de `viscolor.txt`, atalhos Z X C V B,
setas para volume/busca.

**Aceite:** com `--metricas`, ≥ 30 fps tocando música; a captura mostra o analisador animado.

### [ ] F1.7 Playlist
**Fazer:** janela de playlist com as cores de `pledit.txt`, lendo uma pasta (`~/musica`) ou um `.m3u`;
navegação por teclado; avanço automático de faixa.

**Aceite:** uma pasta com 50 faixas carrega em < 2 s e toca em sequência.

### [ ] F1.8 Troca de skin e equalizador
**Fazer:** tecla para trocar de skin em tempo de execução; equalizador de 10 bandas (`equalizer-10bands`)
com `eqmain.bmp`, se o tempo permitir.

**Aceite:** a troca de skin leva < 1 s e não vaza memória (RSS estável após 20 trocas).

### [ ] F1.9 `[HUMANO]` Teste de uso
O mantenedor usa o player por alguns minutos no Eee PC e lista ajustes. Tratar a lista antes da fase 2.

---

## Fase 2 — Motor de mostradores

### [ ] F2.1 Interface `Fonte`
**Fazer:** `painel/fontes/base.py`: `dataclass Leitura(t: float, valores: dict[str, float])` e a classe
abstrata `Fonte` com `iniciar()`, `parar()` e `ultima() -> Leitura | None`, rodando em thread própria.
Catálogo de canais com unidade e faixa (`rpm`, `velocidade`, `marcha`, `temp_motor`, `temp_ar`,
`acelerador`, `tensao`, `combustivel_lh`...).

**Aceite:** testes da interface passam.

### [ ] F2.2 `FonteSimulada`
**Fazer:** simulação de motor simples (marcha lenta, aceleração, troca de marcha, aquecimento) a 8 Hz.

**Aceite:** gravação de 60 s produz curvas plausíveis (verificar com um gráfico gerado no PC).

### [ ] F2.3 Formato de gravação e `FonteReplay`
**Fazer:** definir o formato de viagem (SQLite: tabela `leituras(t, canal, valor)` + metadados) — o
mesmo que o carputer vai gravar. `FonteReplay` toca o arquivo no tempo real, com velocidade ajustável.

**Aceite:** gravar 60 s da `FonteSimulada` e reproduzir; os valores batem com os originais.

### [ ] F2.4 Widgets
**Fazer:** em `painel/widgets/`: `Ponteiro` (sprite rotacionado, com cache de ângulos se a F0.8 indicar),
`Barra` (bargraph segmentado), `Digitos` (7 segmentos/fonte bitmap), `LuzEspia` e `Historico` (linha
dos últimos N segundos). Interpolação no widget (aproximação exponencial ao alvo a cada quadro) e
zonas de alerta.

**Aceite:** tela de teste com um widget de cada tipo, alimentada pela `FonteSimulada`, a ≥ 30 fps no Eee PC.

### [ ] F2.5 Formato de tema
**Fazer:** `painel/tema.py`: carrega `temas/<nome>/tema.json` (lista de widgets com tipo, canal,
posição, faixa, sprites e cores) + PNGs; fundo composto e pré-renderizado na carga; validação do JSON
com mensagens de erro claras.

**Aceite:** um tema inválido gera erro legível; um tema válido carrega em < 1 s.

### [ ] F2.6 Três temas
**Fazer:** gerar os assets por código (scripts em `painel/temas/gerar_*.py`, sem imagens de terceiros):
- `vintage`: mostradores analógicos de fundo creme, numeração serifada, ponteiro vermelho;
- `digital80`: bargraph verde/âmbar/vermelho e dígitos de LED;
- `moderno`: arco minimalista com número grande no centro.

Tecla para alternar entre temas sem reiniciar.

**Aceite:** capturas dos três temas no Eee PC; ≥ 30 fps em todos.

### [ ] F2.7 `FonteUDP` (F1)
**Fazer:** `painel/fontes/udp_f1.py`: escuta UDP na porta 20777 e decodifica o pacote de telemetria do
carro (rpm, velocidade, marcha, acelerador, temperatura do motor). O formato muda a cada edição do jogo:
perguntar ao mantenedor qual edição ele tem e usar a especificação oficial dela. Incluir um gravador de
pacotes brutos para testes offline.

**Aceite:** um teste reproduz pacotes gravados e obtém valores corretos.

### [ ] F2.8 `[HUMANO]` Corrida de teste
O mantenedor configura o jogo para enviar telemetria ao IP do Eee PC e faz uma corrida.

**Aceite:** o painel acompanha o jogo em tempo real nos três temas, sem atraso perceptível.

---

## Fase 3 — Carputer

### [ ] F3.1 `FonteOBD` contra o emulador
**Fazer:** `painel/fontes/obd.py` com `python-OBD` assíncrono. Agendador por prioridade: `rpm` e
`velocidade` a cada ciclo; `temp_motor`, `temp_ar`, `tensao`, sondas e trims a 1 Hz. Na conexão,
descobrir os PIDs suportados e desativar o resto. Reconexão automática. Testar com o **ELM327-emulator**
expondo uma porta serial virtual.

**Aceite:** com o emulador, o painel mostra os valores e reconecta após o emulador reiniciar.
Taxa efetiva de `rpm` registrada em `docs/estado.md`.

### [ ] F3.2 Consumo e códigos de erro
**Fazer:** consumo instantâneo e médio calculados pelo MAF (ou por MAP + temperatura do ar + rotação,
com a cilindrada configurável); tela de códigos de erro (ler, mostrar a descrição, apagar com confirmação).

**Aceite:** cálculo coberto por testes com valores conhecidos; tela de erros funcional com o emulador.

### [ ] F3.3 `[HUMANO]` Primeira leitura no carro
O mantenedor leva o Eee PC + ELM327 USB ao carro (motor ligado, parado) e roda
`python -m painel.fontes.obd --diagnostico`, que lista protocolo, PIDs suportados e taxa de leitura.

**Aceite:** relatório salvo em `docs/carro.md` (modelo, ano, protocolo, PIDs, taxa real).

### [ ] F3.4 Gravação de viagens
**Fazer:** `carputer/gravador.py` grava toda sessão OBD no formato da F2.3, com escrita em lote
(a cada 10 s) para poupar o flash, e um rodízio que apaga as viagens mais antigas acima de 200 MB.

**Aceite:** uma viagem do emulador de 10 minutos gera um arquivo reproduzível pela `FonteReplay`.

### [ ] F3.5 App do carputer
**Fazer:** `carputer/main.py` junta tudo: painel (tema escolhido), aba do player, tela de erros e modo
noturno. Navegação por poucas teclas grandes (pensando em teclado numérico USB no carro).

**Aceite:** ≥ 30 fps com OBD (emulador) + áudio tocando ao mesmo tempo.

### [ ] F3.6 Servidor de viagens
**Fazer:** `servidor/`: API FastAPI (`POST /viagens` com token, `GET /viagens`) + PostgreSQL + página
simples com lista de viagens, gráficos de rpm/velocidade e consumo médio. `Dockerfile` pronto para qualquer host Docker.

**Aceite:** a API roda localmente com `docker compose`, e um upload de viagem de teste aparece na página.
O deploy em produção fica a cargo do mantenedor (`[HUMANO]`), com as variáveis listadas no README.

### [ ] F3.7 Sincronização
**Fazer:** `carputer/sincronizar.py` + timer systemd: quando o SSID atual (`iwgetid -r`) for o de casa
(em `.env`), envia as viagens pendentes e marca como enviadas. Tolerante a queda de rede.

**Aceite:** com o Eee PC no Wi-Fi de casa, as viagens do emulador aparecem no servidor sem intervenção.

### [ ] F3.8 Desligamento seguro
**Fazer:** `carputer/energia.py` monitora o sinal de ignição (por GPIO de um ESP8266 via serial ou por
optoacoplador num adaptador USB-serial; definir com o mantenedor) e, ao perder o sinal por 10 s, fecha a
viagem e executa `sudo poweroff`.

**Aceite:** simulando a queda do sinal, o Eee PC salva a viagem e desliga sozinho em < 30 s.

### [ ] F3.9 `[HUMANO]` Instalação física
O mantenedor instala o step-down 12 V → 9,5 V (ajustado e medido com multímetro **antes** de ligar no
Eee PC), o detector de ignição e o suporte no painel.

### [ ] F3.10 `[HUMANO]` Volta no quarteirão
**Aceite final:** painel em tempo real durante o trajeto; ao chegar em casa, a viagem aparece sozinha
no painel do servidor.
