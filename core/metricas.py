"""Métricas do processo: fps médio, CPU e memória (RSS), impressas a cada 5 s.

No Linux lê `/proc/self/stat` (tempo de CPU) e `/proc/self/status` (VmRSS). Em outros sistemas
(desenvolvimento no PC) cai para `time.process_time()` e informa a memória como indisponível.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

INTERVALO_S = 5.0

_TICKS_POR_S: int = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100


def cpu_processo_s() -> float:
    """Tempo de CPU (usuário + sistema) consumido pelo processo, em segundos."""
    try:
        with open("/proc/self/stat", "rb") as f:
            dados = f.read()
    except OSError:
        return time.process_time()
    # O nome do processo (campo 2) fica entre parênteses e pode ter espaços: corta depois do ')'.
    campos = dados[dados.rfind(b")") + 2 :].split()
    utime, stime = int(campos[11]), int(campos[12])  # campos 14 e 15 do proc(5)
    return (utime + stime) / _TICKS_POR_S


def rss_mb() -> float | None:
    """Memória residente do processo em MB, ou None se não houver /proc."""
    try:
        with open("/proc/self/status", "rb") as f:
            for linha in f:
                if linha.startswith(b"VmRSS:"):
                    return int(linha.split()[1]) / 1024.0  # valor em kB
    except OSError:
        pass
    return None


@dataclass
class Amostra:
    fps: float
    cpu_pct: float
    rss_mb: float | None

    def texto(self) -> str:
        rss = f"{self.rss_mb:6.1f} MB" if self.rss_mb is not None else "   n/d"
        return f"fps {self.fps:5.1f} | cpu {self.cpu_pct:5.1f}% | rss {rss}"


class Metricas:
    """Conta quadros e, a cada `intervalo` segundos, mede e (opcionalmente) imprime uma amostra."""

    def __init__(self, intervalo: float = INTERVALO_S, imprimir: bool = True) -> None:
        self.intervalo = intervalo
        self.imprimir = imprimir
        self.ultima: Amostra | None = None
        self._quadros = 0
        self._t0: float | None = None  # começa no primeiro quadro, fora da inicialização
        self._cpu0 = 0.0

    def quadro(self) -> Amostra | None:
        """Chamar uma vez por quadro. Devolve a amostra nova quando o intervalo fecha."""
        agora = time.monotonic()
        if self._t0 is None:
            self._t0, self._cpu0 = agora, cpu_processo_s()
            return None
        self._quadros += 1
        decorrido = agora - self._t0
        if decorrido < self.intervalo:
            return None
        cpu = cpu_processo_s()
        self.ultima = Amostra(
            fps=self._quadros / decorrido,
            cpu_pct=100.0 * (cpu - self._cpu0) / decorrido,  # um núcleo: 100% = CPU inteira
            rss_mb=rss_mb(),
        )
        self._quadros, self._t0, self._cpu0 = 0, agora, cpu
        if self.imprimir:
            print(self.ultima.texto(), flush=True)
        return self.ultima
