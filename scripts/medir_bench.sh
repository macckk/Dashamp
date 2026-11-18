#!/usr/bin/env bash
# Roda no Eee PC (com o X já aberto em :0): mede as variações do bench do ponteiro (F0.8).
# Para cada variação: métricas do próprio app (fps, CPU, RSS) + CPU total do sistema e do Xorg,
# medidas entre 10 s e 25 s de execução (fora da inicialização).
set -euo pipefail
cd ~/dashamp

cpu_total() { awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8, $5+$6}' /proc/stat; }   # total ocioso
cpu_proc() { awk '{print $14+$15}' "/proc/$1/stat"; }
xorg=$(pgrep -x Xorg | head -1)
hz=$(getconf CLK_TCK)

printf "%-9s %-2s %-8s | %-38s | %6s %6s\n" modo n atualiz "app (últimas amostras)" "sist%" "xorg%"
for modo in rotacao cache; do
  for n in 1 2; do
    for atu in parcial total; do
      log=/tmp/bench_${modo}_${n}_${atu}.log
      DISPLAY=:0 .venv/bin/python -m core.bench_ponteiro --modo "$modo" --mostradores "$n" \
          --atualizacao "$atu" --metricas --duracao 30 >"$log" 2>&1 &
      app=$!
      sleep 10
      read -r t0 i0 < <(cpu_total); x0=$(cpu_proc "$xorg"); s0=$(date +%s.%N)
      sleep 15
      read -r t1 i1 < <(cpu_total); x1=$(cpu_proc "$xorg"); s1=$(date +%s.%N)
      wait "$app" || true
      sist=$(awk -v a="$t0" -v b="$t1" -v c="$i0" -v d="$i1" 'BEGIN{printf "%.1f", 100*(1-(d-c)/(b-a))}')
      xp=$(awk -v a="$x0" -v b="$x1" -v s="$s0" -v e="$s1" -v hz="$hz" 'BEGIN{printf "%.1f", 100*(b-a)/hz/(e-s)}')
      printf "%-9s %-2s %-8s | %-38s | %6s %6s\n" "$modo" "$n" "$atu" "$(grep '^fps' "$log" | tail -2 | head -1)" "$sist" "$xp"
      grep -h '^cache' "$log" || true
    done
  done
done
