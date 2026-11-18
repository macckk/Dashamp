"""Tipos do motor de áudio sem depender do GStreamer (usados também pelo motor falso dos testes)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Tags:
    titulo: str = ""
    artista: str = ""
    kbps: int = 0
    khz: int = 0
    canais: int = 0


@dataclass
class Evento:
    tipo: str          # "fim", "erro", "aviso"
    texto: str = ""
