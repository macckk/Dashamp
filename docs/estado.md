# Estado do Dashamp

Última tarefa concluída: **F0.3** (levantamento da máquina).
Próxima: **F0.4** — pacotes base.

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
