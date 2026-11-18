"""Agrupa as bandas lineares do elemento `spectrum` em barras logarítmicas (o analisador clássico
tem 19 barras de 4 px em 76 px). Puro Python: testável sem GStreamer.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

BARRAS = 19
F_MIN, F_MAX = 40.0, 16000.0
DB_MIN = -60.0  # abaixo disto a barra fica zerada


class Agrupador:
    """Pré-calcula, para cada barra, o intervalo de bandas lineares que ela cobre."""

    def __init__(self, n_bandas: int, taxa: int, n_barras: int = BARRAS,
                 f_min: float = F_MIN, f_max: float = F_MAX) -> None:
        largura_banda = (taxa / 2) / n_bandas
        razao = (f_max / f_min) ** (1 / n_barras)
        self.intervalos: list[tuple[int, int]] = []
        for i in range(n_barras):
            lo = f_min * razao**i
            hi = lo * razao
            a = min(n_bandas - 1, int(lo / largura_banda))
            b = min(n_bandas, max(a + 1, math.ceil(hi / largura_banda)))
            self.intervalos.append((a, b))
        self.n_bandas = n_bandas
        self._barras = [0.0] * n_barras  # reaproveitada: sem alocação por mensagem

    def __call__(self, magnitudes_db: Sequence[float]) -> list[float]:
        """Magnitudes em dB (uma por banda) -> barras 0..1 (pico de cada grupo)."""
        for i, (a, b) in enumerate(self.intervalos):
            pico = max(magnitudes_db[a:b]) if b <= len(magnitudes_db) else DB_MIN
            self._barras[i] = min(1.0, max(0.0, (pico - DB_MIN) / -DB_MIN))
        return list(self._barras)
