"""Motor de áudio falso, com a mesma interface do `MotorAudio`: para testes sem GStreamer."""
from __future__ import annotations

import queue

from player.tipos_audio import Tags


class MotorFalso:
    def __init__(self) -> None:
        self.tags = Tags(titulo="Faixa", artista="Artista", kbps=320, khz=44, canais=2)
        self.eventos: queue.Queue = queue.Queue()
        self.chamadas: list[str] = []
        self._estado = "parado"
        self._volume = 75
        self._balanco = 0
        self.pos = 10.0
        self.dur = 180.0

    def abrir(self, caminho: str) -> None:
        self.chamadas.append(f"abrir {caminho}")
        self._estado = "parado"
        self.pos = 0.0

    def tocar(self) -> None:
        self.chamadas.append("tocar")
        self._estado = "tocando"
        self.pos = max(self.pos, 10.0)

    def pausar(self) -> None:
        self._estado = "pausado"

    def parar(self) -> None:
        self._estado = "parado"

    def buscar(self, segundos: float) -> bool:
        self.pos = max(0.0, segundos)
        return True

    def volume(self, valor: int | None = None) -> int:
        if valor is not None:
            self._volume = max(0, min(100, valor))
        return self._volume

    def balanco(self, valor: int | None = None) -> int:
        if valor is not None:
            self._balanco = valor
        return self._balanco

    def estado(self) -> str:
        return self._estado

    def posicao(self) -> float | None:
        return self.pos if self._estado != "parado" else None

    def duracao(self) -> float | None:
        return self.dur

    def espectro(self) -> list[float] | None:
        return [0.5] * 19 if self._estado == "tocando" else None

    def fechar(self) -> None:
        pass
