#!/usr/bin/env bash
# Abre o app escolhido em ~/dashamp/.app. Chamado em laço pelo ~/.xinitrc (F0.9).
# Formato do .app: uma linha com o nome do app e, opcionalmente, argumentos extras.
#   bench                      -> bench do ponteiro (cache, dois mostradores)
#   bench --metricas           -> idem, imprimindo métricas em /tmp/dashamp.log
#   player [arquivos/pastas]   -> player com skin (padrão: ~/musica)
#   painel [--tema nome]       -> painel de instrumentos com a fonte simulada
#   teste                      -> tela de teste do núcleo
#   (no Eee PC: F1 = player, F2 = painel recebendo o F1 24, F3 = painel com a simulação)
#   nada                       -> nenhum app (X ocioso; para medições sem interferência)
#   <módulo python> [args]     -> qualquer outro módulo, ex.: core.app --metricas
set -u

raiz="$HOME/dashamp"
python="$raiz/.venv/bin/python"   # caminho absoluto: o deploy.sh encerra o app por ele
linha="bench"
[[ -s "$raiz/.app" ]] && linha="$(head -n1 "$raiz/.app")"
read -r nome extras <<<"$linha"

case "$nome" in
    bench) modulo="core.bench_ponteiro"; base=(--modo cache --mostradores 2) ;;
    player) modulo="player.main"; base=() ;;
    painel) modulo="painel.main"; base=() ;;
    teste) modulo="core.app"; base=() ;;
    # Espera o .app mudar (sem precisar matar nada) e sai; o laço do .xinitrc abre o novo app.
    nada)  while [[ "$(head -n1 "$raiz/.app" 2>/dev/null)" == nada* ]]; do sleep 2; done
           exit 0 ;;
    *)     modulo="$nome"; base=() ;;
esac

cd "$raiz" || exit 1
# Os apps usam isto para trocar de app pelas teclas F1/F2/F3 (gravam o .app e saem).
export DASHAMP_ARQUIVO_APP="$raiz/.app"
# Saída no /tmp (tmpfs): nada grava no flash. O arquivo recomeça a cada abertura do app.
# shellcheck disable=SC2086  # extras: argumentos separados por espaço, de propósito
exec "$python" -m "$modulo" "${base[@]}" $extras >/tmp/dashamp.log 2>&1
