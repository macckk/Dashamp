# Estado do Dashamp

Última tarefa concluída: **F0.2** (acesso SSH por chave).
Próxima: **F0.3** — levantamento da máquina.

## Máquina alvo

- Debian 12 instalado (F0.1); OpenSSH 9.2p1 (`Debian-2+deb12u10`).
- IP e usuário ficam só no `~/.ssh/config` do PC de desenvolvimento (alias `eeepc`) e no `.env`.
- Resto do levantamento: F0.3.

## Acesso (F0.2)

- Chave dedicada `~/.ssh/eeepc_ed25519` no PC; `IdentitiesOnly yes` no `Host eeepc`.
- `sudo` sem senha em `/etc/sudoers.d/eeepc` (0440, validado com `visudo -c`).
- `sshd`: drop-in `/etc/ssh/sshd_config.d/10-dashamp.conf` com `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no` e `PermitRootLogin no`. Login por senha recusado (testado).
  Para reverter, apague esse arquivo pelo console local e rode `sudo systemctl reload ssh`.

## Decisões

- **F0.0** — `.gitattributes` com `eol=lf` para todo texto: o PC de desenvolvimento é Windows
  (`core.autocrlf=true`) e scripts com CRLF quebram no Linux do Eee PC.
- **F0.0** — a pasta local `Claude outputs/` (rascunhos de trabalho) fica no `.gitignore`.
