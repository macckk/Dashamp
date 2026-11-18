"""Captura de tela: `--captura N` salva um PNG da janela após N segundos.

No Eee PC o arquivo vai para `/tmp/captura.png` (tmpfs, não gasta o flash). Em sistemas sem `/tmp`
(Windows) vai para a pasta temporária do sistema.
"""
from __future__ import annotations

import os
import tempfile
import time

import pygame

ARQUIVO_PADRAO = "/tmp/captura.png" if os.path.isdir("/tmp") else os.path.join(
    tempfile.gettempdir(), "captura.png"
)


class Captura:
    """Salva a superfície uma única vez, quando o prazo vence."""

    def __init__(self, segundos: float, arquivo: str = ARQUIVO_PADRAO) -> None:
        self.arquivo = arquivo
        self.feita = False
        self._prazo = time.monotonic() + segundos

    def verificar(self, tela: pygame.Surface) -> bool:
        """Chamar depois de desenhar o quadro. Devolve True no quadro em que salvou."""
        if self.feita or time.monotonic() < self._prazo:
            return False
        pygame.image.save(tela, self.arquivo)
        self.feita = True
        print(f"captura salva em {self.arquivo}", flush=True)
        return True
