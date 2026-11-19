# Instalação e uso

**Português** · [English](#english)

O Dashamp roda num Linux antigo com tela, sem ambiente de desktop: o X sobe direto no app. A
referência é um ASUS Eee PC 701 (Celeron M 900 MHz, 32 bits, 512 MB de RAM, tela 800×480); qualquer
máquina com Debian 12 e uma tela de 800×480 ou maior serve.

Há dois jeitos de instalar:

- **com um PC de desenvolvimento** (o jeito do projeto): o código fica no PC e vai para a máquina
  pelo `deploy/deploy.sh`, por SSH;
- **direto na máquina**: clonar o repositório nela e configurar o boot à mão.

## 1. Sistema

1. Instale o **Debian 12** (i386 para máquinas de 32 bits) **sem ambiente de desktop**, com o
   servidor SSH. Crie um usuário comum (o projeto usa `dashamp`).
2. Pacotes (sem os recomendados, para caber em 4 GB de flash):

   ```sh
   sudo apt install --no-install-recommends rsync xserver-xorg-core xserver-xorg-video-intel \
       xinit x11-xserver-utils python3-venv python3-gi gir1.2-gstreamer-1.0 \
       gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
       gstreamer1.0-plugins-ugly gstreamer1.0-alsa alsa-utils unzip sqlite3 htop \
       python3-pygame python3-pycryptodome python3-serial python3-yaml git
   ```

   Troque `xserver-xorg-video-intel` pelo driver da sua placa de vídeo, se não for Intel.
3. Para ler o carro por um adaptador USB, o usuário precisa do grupo `dialout`
   (`sudo usermod -aG dialout $USER`, vale no próximo login).
4. Opcional, mas recomendado em flash: `noatime` no `/etc/fstab`, `/tmp` em tmpfs e o journald com
   `Storage=volatile` (detalhes em [`estado.md`](estado.md), F0.6).

## 2. Código e ambiente Python

```sh
git clone https://github.com/macckk/Dashamp.git ~/dashamp
cd ~/dashamp
python3 -m venv --system-site-packages .venv      # pygame, GStreamer e afins vêm do apt
.venv/bin/pip install --only-binary=:all: -r deploy/requirements.txt
```

O `pygame` é o 2.1.2 do Debian: o wheel do pygame-ce para 32 bits usa instruções que um Celeron M
não tem. O `requirements.txt` traz o python-OBD (leitura do carro) e o emulador ELM327 (só para
testes).

Teste rápido: `DISPLAY=:0 .venv/bin/python -m painel.main --janela` (com o X rodando) ou rode os
testes com `.venv/bin/python -m pytest testes` (precisa do `pip install pytest`).

## 3. Ligar direto no app

O boot abre o X no tty1 com login automático, e o X roda `deploy/run.sh` em laço; o `run.sh` lê
`~/dashamp/.app` para saber qual app abrir.

- **Com o PC de desenvolvimento:** configure o alias `eeepc` no `~/.ssh/config` do PC (ou
  `DASHAMP_HOST_ALVO` no `.env`, veja `.env.exemplo`) e rode `./deploy/instalar_boot.sh`.
- **Direto na máquina:** copie `deploy/sistema/bash_profile` para `~/.bash_profile` e
  `deploy/sistema/xinitrc` para `~/.xinitrc` (com `chmod +x`); instale
  `deploy/sistema/getty-autologin.conf` em `/etc/systemd/system/getty@tty1.service.d/override.conf`
  trocando `__USUARIO__` pelo seu usuário; `sudo systemctl daemon-reload` e reinicie.

Escolha o app inicial com uma linha em `~/dashamp/.app`, por exemplo `player`,
`painel --tema vintage`, `painel --gt7` ou `painel --obd`.

## 4. Uso

### Trocar de app (em qualquer app)

| Tecla | App |
| --- | --- |
| **F1** | Player de música |
| **F2** | Painel recebendo o **Gran Turismo 7** do PS5 (veja [`jogos.md`](jogos.md)) |
| **F3** | Painel com a simulação (demonstração) |
| **F4** | Painel lendo o **carro** pelo adaptador OBD-II |
| **F5** | Diagnóstico do carro (protocolo, PIDs, taxa de leitura; relatório em `~/dashamp/.dados`) |
| **Esc / Q** | Sai do app (o laço do boot abre de novo) |

A escolha fica gravada: a máquina liga no último app usado.

### Player

Toca `~/musica` (pastas, arquivos ou `.m3u`). Skins clássicas `.wsz` em `player/skins_teste/`
(baixe as de teste com `scripts/baixar_skins.sh`; o projeto não distribui skins de terceiros).

- **Z X C V B**: anterior, tocar, pausar, parar, próxima · **S** aleatório · **R** repetir
- **↑/↓** volume · **←/→** volta/avança 5 s · **Tab** troca o foco entre as janelas
- **L** playlist grande · **E** playlist ou equalizador · **K** próxima skin

### Painel

- **T** troca de tema (vintage, digital80, moderno); o tema escolhido fica gravado.
- Com o carro (**F4**): **E** abre os códigos de erro (**L** lê de novo, **A** apaga com
  confirmação, **E** volta).
- Enquanto não chegam dados, uma caixa diz o que falta (rede, console, adaptador, ignição).

Opções úteis de `python -m painel.main`: `--tema`, `--gt7 [--ps5 IP]`, `--udp` (F1 24),
`--obd [PORTA]`, `--combustivel gasolina|gasolina_br|etanol`, `--cilindrada L` (consumo em carro
sem sensor MAF), `--replay viagem.db`, `--metricas`, `--captura S`, `--janela`.

### Adaptador do carro

Use um **ELM327 USB v1.5** (de preferência com o chip PIC18F25K80). Evite os "v2.1" (cópias que
não aceitam todos os comandos). Bluetooth funciona, mas precisa de rádio Bluetooth na máquina e
de parear antes (`/dev/rfcomm0`).

---

## English

Dashamp runs on an old Linux box with a screen and no desktop environment: X starts straight into
the app. Reference machine: ASUS Eee PC 701 (900 MHz Celeron M, 32-bit, 512 MB RAM, 800×480).

1. **System**: install Debian 12 (i386 on 32-bit machines) without a desktop, with SSH. Install
   the packages listed in step 1 above (`--no-install-recommends`). Add your user to `dialout`
   for a USB OBD-II adapter.
2. **Code**: clone into `~/dashamp`, create the venv with `--system-site-packages` (pygame,
   GStreamer and friends come from apt) and `pip install --only-binary=:all: -r
   deploy/requirements.txt`.
3. **Boot**: run `./deploy/instalar_boot.sh` from a development PC over SSH, or copy the files in
   `deploy/sistema/` by hand (autologin on tty1, `.bash_profile` starts X, `.xinitrc` loops
   `deploy/run.sh`). The first line of `~/dashamp/.app` picks the app.
4. **Keys**: F1 music player, F2 Gran Turismo 7 dashboard (PS5, see [`jogos.md`](jogos.md#english)),
   F3 simulated dashboard, F4 car dashboard (OBD-II), F5 car diagnostics. In the dashboard, **T**
   changes the theme and **E** (car only) shows trouble codes. Player: Z X C V B transport, ↑/↓
   volume, L/E/K playlist, equalizer, next skin.
5. **Car adapter**: an ELM327 **USB v1.5** (PIC18F25K80) is recommended; avoid "v2.1" clones.
