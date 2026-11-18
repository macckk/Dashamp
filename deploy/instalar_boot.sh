#!/usr/bin/env bash
# F0.9: configura o Eee PC para ligar direto no app. Roda no PC; repetir é seguro.
#   - autologin no tty1 (override do getty@tty1);
#   - ~/.bash_profile abre o X no tty1; ~/.xinitrc roda deploy/run.sh em laço;
#   - cria ~/dashamp/.app com "bench" se ainda não existir.
# Arquivos existentes diferentes dos do projeto ganham cópia de segurança (*.antes-dashamp).
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
"$raiz/deploy/deploy.sh"
host="eeepc"
if [[ -f "$raiz/.env" ]]; then
    valor="$(grep -E '^DASHAMP_HOST_ALVO=' "$raiz/.env" | tail -1 | cut -d= -f2- || true)"
    host="${valor:-$host}"
fi

ssh "$host" '
set -e
s=~/dashamp/deploy/sistema
instalar() {  # instalar <origem> <destino>
    if [ -f "$2" ] && ! cmp -s "$1" "$2"; then cp -a "$2" "$2.antes-dashamp"; fi
    cp "$1" "$2"
}
instalar $s/bash_profile ~/.bash_profile
instalar $s/xinitrc ~/.xinitrc
chmod +x ~/.xinitrc
[ -s ~/dashamp/.app ] || echo bench > ~/dashamp/.app

d=/etc/systemd/system/getty@tty1.service.d
sed "s/__USUARIO__/$(id -un)/" $s/getty-autologin.conf > /tmp/override.conf
sudo install -d $d
sudo install -m 0644 /tmp/override.conf $d/override.conf
rm -f /tmp/override.conf
sudo systemctl daemon-reload
systemctl cat getty@tty1 | grep "^ExecStart=-"
echo "boot direto configurado; app atual: $(cat ~/dashamp/.app)"
'
