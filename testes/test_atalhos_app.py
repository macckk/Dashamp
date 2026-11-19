"""Teclas F1/F2/F3 para trocar de app e o tema lembrado no .app (uso no Eee PC sem SSH)."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pygame
import pytest

from core import app as ca


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    arq = tmp_path / ".app"
    arq.write_text("painel --udp --tema moderno\n", encoding="utf-8")
    monkeypatch.setenv("DASHAMP_ARQUIVO_APP", str(arq))
    a = ca.App(argparse.Namespace(janela=False, metricas=False, captura=None, duracao=None))
    yield a, arq
    pygame.display.quit()


def _tecla(a: ca.App, k: int) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))
    a._tratar_eventos(None)


def test_f1_abre_o_player(app) -> None:
    a, arq = app
    _tecla(a, pygame.K_F1)
    assert not a.rodando and arq.read_text(encoding="utf-8") == "player\n"


def test_f3_e_f2_mantem_o_tema(app) -> None:
    a, arq = app
    _tecla(a, pygame.K_F3)
    assert arq.read_text(encoding="utf-8") == "painel --tema moderno\n"
    a.rodando = True
    _tecla(a, pygame.K_F2)
    assert arq.read_text(encoding="utf-8") == "painel --gt7 --tema moderno\n"


def test_lembra_o_tema(app) -> None:
    _, arq = app
    ca.lembrar_opcao("--tema", "vintage")
    assert arq.read_text(encoding="utf-8") == "painel --udp --tema vintage\n"
    arq.write_text("painel --udp\n", encoding="utf-8")
    ca.lembrar_opcao("--tema", "digital80")
    assert arq.read_text(encoding="utf-8") == "painel --udp --tema digital80\n"


def test_sem_run_sh_as_teclas_nao_fazem_nada(app, monkeypatch: pytest.MonkeyPatch) -> None:
    a, arq = app
    monkeypatch.delenv("DASHAMP_ARQUIVO_APP")
    _tecla(a, pygame.K_F1)
    assert a.rodando and "painel" in arq.read_text(encoding="utf-8")
    ca.lembrar_opcao("--tema", "x")                # no PC de desenvolvimento: nada é gravado
    assert "moderno" in arq.read_text(encoding="utf-8")
