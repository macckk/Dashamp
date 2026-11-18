# Estado do Dashamp

Última tarefa concluída: **F0.8** (teste decisivo de desempenho).
Próxima: **F0.9** — boot direto no app.

## Desempenho (F0.8, 2026-11-18)

`core/bench_ponteiro.py`: mostrador 400×400 pré-renderizado + ponteiro (sprite 338×18 com alfa) +
cubo central + texto de fps. Medido por `scripts/medir_bench.sh` no Eee PC, entre 10 s e 25 s de
execução. "parcial" = redesenha só os retângulos que mudam; "total" = tela inteira a cada quadro.
CPU do app é do processo Python; "sistema" inclui o Xorg (que copia os quadros via XShm).

| Ponteiro | Mostradores | Atualização | fps | CPU app | CPU sistema | Xorg | RSS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rotate a cada quadro | 1 | parcial | 30,2 | 44% | 49% | 3% | 48 MB |
| rotate a cada quadro | 1 | total | 30,2 | 52% | 62% | 9% | 48 MB |
| rotate a cada quadro | 2 | parcial | **28,6** | 81% | **86%** | 4% | 49 MB |
| rotate a cada quadro | 2 | total | **27,4** | 83% | **91%** | 8% | 49 MB |
| cache de 360 ângulos | 1 | parcial | 30,2 | 15% | 18% | 1% | 67 MB |
| cache de 360 ângulos | 1 | total | 30,2 | 24% | 35% | 9% | 67 MB |
| **cache de 360 ângulos** | **2** | **parcial** | **30,1** | **29%** | **32%** | 2% | **68 MB** |
| cache de 360 ângulos | 2 | total | 30,2 | 38% | 49% | 9% | 67 MB |

**Aceite atingido**: dois mostradores em tela cheia a 30 fps com 32% de CPU do sistema (parcial)
ou 49% (redesenhando tudo). Conclusões para as fases 1–3:

- **Ponteiros usam cache de ângulos**, nunca `transform.rotate` por quadro: a rotação sozinha custa
  ~20% de CPU por ponteiro e dois deles já estouram o orçamento.
- O cache (gerado com `rotozoom`, antisserrilhado, e recortado ao conteúdo) custa **18 MB e 2,3 s
  de carga por desenho de ponteiro**. Dois mostradores com o mesmo ponteiro dividem o cache. Para
  vários ponteiros diferentes: gerar só os ângulos da varredura (270°), ou guardar o cache em disco.
- **Atualização parcial** economiza 10–17 pontos de CPU (principalmente no Xorg). Vale manter.
- Folga para áudio + espectro + OBD na F3.5: ~65% de CPU e ~50 MB de RAM no orçamento de 120 MB.

## Núcleo (F0.7)

- **pygame-ce trocado pelo `python3-pygame` 2.1.2 do apt** (SDL 2.26.5; 68,5 MB, aprovado pelo
  mantenedor). O wheel i686 do pygame-ce importa, mas morre com *instrução ilegal* em
  `pygame.display.init()` com o driver X11: o kernel aponta o `libSDL2` embutido no wheel
  (`trap invalid opcode ... in libSDL2-2-44947314.0.so`). Com `SDL_VIDEODRIVER=dummy` não falha.
  O Debian compila para a base i686, que o Celeron M (só até SSE2) suporta.
- No PC de desenvolvimento continua o pygame-ce (`deploy/requirements-pc.txt`), porque o pygame 2.1.2
  não tem wheel para Pythons novos. **O código deve usar só a API do pygame 2.1.2.**
- **`SDL_FRAMEBUFFER_ACCELERATION=0`** (definido em `core/app.py`): sem ele o SDL apresenta a janela
  por OpenGL e carrega Mesa `i915_dri` + `libLLVM-15` (~58 MB). Medido na tela de teste:

  | | fps | CPU | RSS |
  | --- | --- | --- | --- |
  | padrão (OpenGL) | 30,2 | 6,5% | 119 MB |
  | `SDL_FRAMEBUFFER_ACCELERATION=0` (XShm) | 30,2 | 2,0% | 49 MB |

- `pygame.display.init()` + `pygame.font.init()` em vez de `pygame.init()`: não abre o mixer, que
  prenderia o ALSA (o áudio é do GStreamer).
- Opções comuns de todo app: `--metricas`, `--captura N`, `--duracao N` (encerra sozinho; para
  medições pelo SSH) e `--janela` (bordas e cursor, no PC).
- Teste pelo SSH: o X sobe como root com
  `sudo xinit /bin/sh -c "xhost +si:localuser:dashamp; exec sleep 900" -- :0 vt1` e o app roda como
  `dashamp` com `DISPLAY=:0`. Captura conferida (800×480 inteiros, animação, 30 fps).
- Ainda não verificado: sair com Esc/Q no teclado físico (pelo SSH não há como apertar a tecla;
  fica para a conferência da F0.10).

## Flash (F0.6)

- `fstab` (backup em `/etc/fstab.antes-f06`, validado com `findmnt --verify`):
  `noatime` no `/`; `/tmp` em tmpfs de 100 MB (`nosuid,nodev,noatime`); **swap comentada**
  (a partição `sda5` continua lá, só não é usada; o `RESUME=` do initramfs aponta para ela e é inofensivo).
- journald: `/etc/systemd/journald.conf.d/10-dashamp.conf` com `Storage=volatile` e
  `RuntimeMaxUse=16M`; journal antigo do flash (`/var/log/journal`, 17 MB) apagado com aprovação.
- Desativados (aprovados pelo mantenedor): `bluetooth` (sem hardware), `wpa_supplicant` (Wi-Fi
  não detectado; religar na F3.7 se aparecer), `apt-daily` e `apt-daily-upgrade` (atualizações agora
  manuais), `man-db`, `anacron`, `dpkg-db-backup`, `e2scrub_all`/`e2scrub_reap` (sem LVM) e
  `fstrim` (o flash não aceita TRIM).
- Mantidos: `ssh`, `networking`, `getty`, `cron`, `logrotate`, `systemd-timesyncd`, `apparmor`,
  `console-setup`, `keyboard-setup`, `systemd-pstore`.
- Após o reboot: SSH de volta em ~45 s; boot de 28,8 s (13,1 s kernel + 15,7 s userspace);
  nenhuma unidade com falha; 435 MB de RAM disponíveis ociosa; 1,6 GB livres.

## Venv e deploy (F0.5)

- ~~pygame-ce 2.5.8 pelo pip~~ (wheel `manylinux2014_i686`): importava, mas não abre janela no
  Eee PC; substituído pelo `python3-pygame` do apt na F0.7.
- **Venv com `--system-site-packages`**: o `gi` (PyGObject) e o GStreamer 1.22 vêm do apt; sem a
  opção, o venv não os enxerga. Venv: 59 MB. `spectrum` e `playbin` disponíveis.
- **`deploy/deploy.sh`**: usa `rsync` se existir no PC; o Git Bash do Windows não tem, então cai
  para `tar` pelo SSH, extraindo em `~/dashamp/.novo` e trocando o conteúdo (espelho: arquivos
  apagados no PC somem no Eee PC). `.venv` e `.app` são preservados; nada é apagado fora de
  `~/dashamp`. `--deps` instala `deploy/requirements.txt`. O host vem de `DASHAMP_HOST_ALVO` no
  `.env` (padrão `eeepc`).
- O reinício usa `pkill -f "[d]ashamp.main"`: sem o colchete, o `pkill` mataria o próprio shell
  remoto, cuja linha de comando contém o padrão.

## Pacotes base (F0.4)

- Kernel antigo `6.1.0-39` removido e cache do apt limpo antes da instalação (1,6 → 1,9 GB livres);
  o GRUB só lista o kernel atual.
- 164 pacotes da lista do plano, sem recomendados: 326 MB. Depois: **1,6 GB livres** em `/`.
- **Extra: `xserver-xorg-input-libinput`** (1,8 MB). Sem ele o X ignora teclado e touchpad
  ("No input driver specified") e o app não receberia Esc/Q.
- X: driver `intel` (915GM), saída `LVDS1` em 800×480; teclado e touchpad via libinput.
- Pelo SSH, o X só sobe como root (usuário comum recebe "Switching VT failed"); no boot (F0.9)
  ele sobe pelo autologin no tty1. O teste de aceite foi feito com `sudo xinit ...`.
- Som: `speaker-test -c2 -l1` toca nos dois canais (confirmado de ouvido pelo mantenedor).
  O mixer só tem `Master` (sem `PCM`), deixado em 80%.

## Máquina alvo (levantamento F0.3, 2026-11-18)

| Item | Valor |
| --- | --- |
| Sistema | Debian 12.15 i386, Python 3.11.2 |
| Kernel | `6.1.0-56-686-pae` (6.1.192-2) — ver nota abaixo |
| CPU | Intel Celeron M 900 MHz, 1 núcleo, 32 bits; flags `sse sse2 pae nx` (sem `ssse3`/`sse4`) |
| **RAM** | **512 MB** (482 MB visíveis ao sistema; ~434 MB disponíveis ociosa) |
| Armazenamento | flash de 3,7 GB: `sda1` 3,2 GB ext4 em `/` + `sda5` 501 MB de swap |
| **Espaço livre em `/`** | **1,6 GB** (1,4 GB usados) |
| Vídeo | Intel 915GM (driver `i915`) |
| Áudio | HDA Intel ICH6 (`snd_hda_intel`), placa 0 |
| Rede | Ethernet Atheros L2 (`atl2`), 100 Mbit |
| Wi-Fi | **não detectado** no barramento PCI (ver nota) |
| USB | webcam integrada (eMPIA), leitor SD (ENE UB6225) |

### Orçamento de memória

Com 512 MB de RAM, o orçamento do app gráfico **cai para RSS ≤ 120 MB** (em vez de 150 MB).

### Notas do levantamento

- **Kernel PAE**: o plano previa o kernel `686` sem PAE, mas esta CPU anuncia `pae` e `nx`, e o
  instalador escolheu `686-pae`, que dá boot normalmente. Com PAE o bit NX (proteção de memória)
  funciona; o custo em 512 MB de RAM é desprezível. Decisão pendente com o mantenedor.
- **Swap**: o instalador criou uma partição de swap de 501 MB (`sda5`), contra o plano.
  Swap no flash gasta a vida útil; a proposta é desligá-la na F0.6 (`swapoff` + linha comentada
  no `fstab`), sem mexer na partição.
- **Kernel antigo**: `6.1.0-39-686-pae` ainda instalado (~186 MB de módulos) e há 76 MB de cache do
  apt. Remover ambos libera ~250 MB antes da F0.4, cujo aceite pede ≥ 1,5 GB livres.
- **Wi-Fi**: nenhuma placa sem fio aparece no `lspci`. Pode estar desativada no BIOS
  (opção de WLAN on-board) ou ausente. Só é necessária na F3.7; investigar antes dela.
- `aplay` ainda não está instalado (vem com `alsa-utils` na F0.4).

## Acesso (F0.2)

- Chave dedicada `~/.ssh/eeepc_ed25519` no PC; `IdentitiesOnly yes` no `Host eeepc`.
- IP e usuário ficam só no `~/.ssh/config` do PC de desenvolvimento e no `.env`.
- `sudo` sem senha em `/etc/sudoers.d/eeepc` (0440, validado com `visudo -c`).
- `sshd`: drop-in `/etc/ssh/sshd_config.d/10-dashamp.conf` com `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no` e `PermitRootLogin no`. Login por senha recusado (testado).
  Para reverter, apague esse arquivo pelo console local e rode `sudo systemctl reload ssh`.

## Decisões

- **F0.0** — `.gitattributes` com `eol=lf` para todo texto: o PC de desenvolvimento é Windows
  (`core.autocrlf=true`) e scripts com CRLF quebram no Linux do Eee PC.
- **F0.0** — a pasta local `Claude outputs/` (rascunhos de trabalho) fica no `.gitignore`.
