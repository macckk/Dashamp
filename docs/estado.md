# Estado do Dashamp

Última tarefa concluída: **F0.6** (proteger o flash).
Próxima: **F0.7** — núcleo mínimo: janela, métricas e captura.

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

- **pygame-ce 2.5.8 pelo pip**: há wheel `manylinux2014_i686` para cp311 (traz o próprio SDL 2.32.10),
  então o `python3-pygame` do apt não foi necessário. Instalar sempre com `--only-binary=:all:`.
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
