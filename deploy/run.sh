#!/usr/bin/env bash
# Abre o app escolhido em ~/dashamp/.app. Chamado em laço pelo ~/.xinitrc (F0.9).
# Formato do .app: uma linha com o nome do app e, opcionalmente, argumentos extras.
#   bench                      -> bench do ponteiro (cache, dois mostradores)
#   bench --metricas           -> idem, imprimindo métricas em /tmp/dashamp.log
#   teste                      -> tela de teste do núcleo
#   <módulo python> [args]     -> qualquer outro módulo, ex.: core.app --metricas
set -u

raiz="$HOME/dashamp"
python="$raiz/.venv/bin/python"   # caminho absoluto: o deploy.sh encerra o app por ele
linha="bench"
[[ -s "$raiz/.app" ]] && linha="$(head -n1 "$raiz/.app")"
read -r nome extras <<<"$linha"

case "$nome" in
    bench) modulo="core.bench_ponteiro"; base=(--modo cache --mostradores 2) ;;
    teste) modulo="core.app"; base=() ;;
    *)     modulo="$nome"; base=() ;;
esac

cd "$raiz" || exit 1
# Saída no /tmp (tmpfs): nada grava no flash. O arquivo recomeça a cada abertura do app.
# shellcheck disable=SC2086  # extras: argumentos separados por espaço, de propósito
exec "$python" -m "$modulo" "${base[@]}" $extras >/tmp/dashamp.log 2>&1
