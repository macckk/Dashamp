#!/usr/bin/env bash
# Baixa as skins clássicas de teste (.wsz) do Winamp Skin Museum (https://skins.webamp.org/)
# para player/skins_teste/. Essa pasta está no .gitignore: as skins são de terceiros e
# NUNCA vão para o repositório.
#
# Cada skin é fixada pelo MD5 (o Museum identifica as skins por ele) e conferida após o download.
# Roda no PC (Git Bash) e no Eee PC. Repetir é seguro: arquivos já corretos não são baixados.
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
destino="$raiz/player/skins_teste"
base_url="https://r2.webampskins.org/skins"

# nome local | md5 no Museum | descrição
skins=(
    "base-2.91.wsz|5e4f10275dcb1fb211d4a8b4f1bda236|padrão do Winamp 2.91 (referência e fallback)"
    "winamp5_classified.wsz|b0fb83cc20af3abe264291bb17fb2a13|Winamp5 Classified v5.5 (escura, moderna)"
    "zelda_amp_3.wsz|d770a634cc1ab252cfb16c64f4f5f616|Zelda Amp 3 (temática, bem diferente)"
)

baixar() {  # baixar <url> <arquivo>
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 -o "$2" "$1"
    else
        wget -q -O "$2" "$1"
    fi
}

md5() { md5sum "$1" | cut -d' ' -f1; }

mkdir -p "$destino"
falhas=0
for item in "${skins[@]}"; do
    IFS='|' read -r nome soma descricao <<<"$item"
    arquivo="$destino/$nome"
    # Screenshot do Museum (renderizado pelo Webamp): referência visual da F1.4.
    png="$destino/${nome%.wsz}.png"
    if [[ ! -s "$png" ]]; then
        baixar "https://r2.webampskins.org/screenshots/$soma.png" "$png" || rm -f "$png"
    fi
    if [[ -f "$arquivo" && "$(md5 "$arquivo")" == "$soma" ]]; then
        echo "ok (já existe)  $nome — $descricao"
        continue
    fi
    if baixar "$base_url/$soma.wsz" "$arquivo.parcial" && [[ "$(md5 "$arquivo.parcial")" == "$soma" ]]; then
        mv "$arquivo.parcial" "$arquivo"
        echo "ok (baixada)    $nome — $descricao"
    else
        rm -f "$arquivo.parcial"
        echo "FALHOU          $nome ($base_url/$soma.wsz)" >&2
        falhas=$((falhas + 1))
    fi
done

if ((falhas)); then
    echo "$falhas skin(s) não baixada(s). Se o site bloquear, baixe manualmente pelo Museum" \
         "e salve em player/skins_teste/ com os nomes acima." >&2
    exit 1
fi
