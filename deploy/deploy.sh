#!/usr/bin/env bash
# Envia o repositório para o Eee PC (~/dashamp) e reinicia o app.
# Uso: ./deploy/deploy.sh [--deps]
#   --deps  também instala/atualiza deploy/requirements.txt no venv do Eee PC.
# Usa rsync quando existe no PC; senão (Git Bash no Windows), tar pelo SSH com troca atômica
# da pasta, preservando o venv, a escolha de app (.app) e os dados gravados no Eee PC (.dados:
# relatórios de diagnóstico, viagens).
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
host="eeepc"
if [[ -f "$raiz/.env" ]]; then
    valor="$(grep -E '^DASHAMP_HOST_ALVO=' "$raiz/.env" | tail -1 | cut -d= -f2- || true)"
    host="${valor:-$host}"
fi

excluir=(.git .venv __pycache__ '*.pyc' tmp 'Claude outputs' .app .dados)

if command -v rsync >/dev/null 2>&1; then
    args=()
    for e in "${excluir[@]}"; do args+=(--exclude="$e"); done
    rsync -az --delete "${args[@]}" "$raiz/" "$host:dashamp/"
else
    args=()
    for e in "${excluir[@]}"; do args+=(--exclude="$e"); done
    # Extrai em ~/dashamp/.novo e só então troca o conteúdo; tudo que é apagado fica dentro
    # de ~/dashamp (regra 6 do CLAUDE.md). .venv, .app e .dados nunca são tocados.
    tar -cz "${args[@]}" -C "$raiz" . | ssh "$host" '
        set -e
        cd ~ && mkdir -p dashamp && cd dashamp
        rm -rf .novo && mkdir .novo
        tar -xzf - -C .novo
        find . -mindepth 1 -maxdepth 1 ! -name .venv ! -name .app ! -name .dados ! -name .novo -exec rm -rf {} +
        find .novo -mindepth 1 -maxdepth 1 -exec mv {} . \;
        rmdir .novo
        find . -path ./.venv -prune -o -name "*.sh" -exec chmod +x {} +'
fi

if [[ "${1:-}" == "--deps" ]]; then
    ssh "$host" 'cd ~/dashamp && .venv/bin/pip install -q --only-binary=:all: -r deploy/requirements.txt'
fi

# Encerra o app; o laço do ~/.xinitrc o abre de novo. O run.sh chama o Python do venv por
# caminho absoluto, então o padrão pega só os apps do projeto. O colchete evita que o pkill
# case com o próprio shell remoto, cuja linha de comando contém o padrão.
ssh "$host" 'pkill -f "[/]dashamp/.venv/bin/python -m" || true'
echo "deploy ok -> $host:~/dashamp"
