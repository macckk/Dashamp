"""Testes da tela de códigos de erro (F3.2), com uma fonte falsa e o display "dummy" do SDL."""
from __future__ import annotations

import os
from concurrent.futures import Future

import pygame
import pytest

from carputer import tela_erros as te
from painel.fontes.obd import SemConexao


@pytest.fixture(autouse=True)
def tela():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    yield pygame.display.set_mode((800, 480))
    pygame.display.quit()


def _pronto(valor=None, erro: Exception | None = None) -> Future:
    f: Future = Future()
    if erro is not None:
        f.set_exception(erro)
    else:
        f.set_result(valor)
    return f


class FonteFalsa:
    def __init__(self) -> None:
        self.codigos = {"armazenados": [("P0143", "O2 Sensor Circuit Low Voltage"),
                                        ("P1234", "")],
                        "pendentes": [("C0035", "")]}
        self.aceita = True
        self.apagadas = 0
        self.manual: Future | None = None       # para segurar uma resposta

    def ler_erros(self) -> Future:
        return self.manual or _pronto({k: list(v) for k, v in self.codigos.items()})

    def apagar_erros(self) -> Future:
        if self.aceita:
            self.apagadas += 1
            self.codigos = {k: [] for k in self.codigos}
        return _pronto(self.aceita)


def _texto_na_tela(tela: pygame.Surface, area: tuple[int, int, int, int]) -> bool:
    """Há pixel de texto (diferente do fundo) na área?"""
    x0, y0, x1, y1 = area
    return any(tela.get_at((x, y))[:3] != te.COR_FUNDO
               for x in range(x0, x1, 2) for y in range(y0, y1, 2))


def test_sistema_do_codigo() -> None:
    assert te.sistema("P0143") == "motor e câmbio, genérico"
    assert te.sistema("P1234") == "motor e câmbio, do fabricante"
    assert te.sistema("U0100") == "rede de módulos, genérico"
    assert te.sistema("X") == "desconhecido"


def test_ler_confirmar_e_apagar(tela) -> None:
    fonte = FonteFalsa()
    t = te.TelaErros(fonte)
    t.abrir()
    assert t.ativa and t.desenhar(tela) is None         # redesenhou tudo
    assert t.estado == "lista" and t._total() == 3
    assert t.desenhar(tela) == []                       # nada mudou: não redesenha
    assert _texto_na_tela(tela, (24, 100, 120, 140))    # código na primeira linha
    t.tecla(pygame.K_a)
    assert t.estado == "confirmar"
    t.tecla(pygame.K_n)                                 # cancelou
    assert t.estado == "lista" and fonte.apagadas == 0
    t.tecla(pygame.K_a)
    t.tecla(pygame.K_s)
    assert t.estado == "apagando"
    t.desenhar(tela)                                    # resposta: apagou → lê de novo
    t.desenhar(tela)
    assert fonte.apagadas == 1 and t.estado == "lista" and t._total() == 0
    t.tecla(pygame.K_a)                                 # nada para apagar
    assert t.estado == "lista"
    assert t.tecla(pygame.K_e) is True and not t.ativa


def test_central_recusa_e_falta_de_conexao(tela) -> None:
    fonte = FonteFalsa()
    fonte.aceita = False
    t = te.TelaErros(fonte)
    t.abrir()
    t.desenhar(tela)
    t.tecla(pygame.K_a)
    t.tecla(pygame.K_s)
    t.desenhar(tela)
    assert t.estado == "falha" and "recusou" in t.mensagem
    fonte.manual = _pronto(erro=SemConexao("o carro não está conectado"))
    t.tecla(pygame.K_l)
    t.desenhar(tela)
    assert t.estado == "falha" and "conectado" in t.mensagem


def test_desiste_sem_resposta(tela, monkeypatch) -> None:
    fonte = FonteFalsa()
    fonte.manual = Future()                             # nunca responde
    t = te.TelaErros(fonte)
    t.abrir()
    t.desenhar(tela)
    assert t.estado == "lendo"
    monkeypatch.setattr(te, "ESPERA_MAX_S", -1.0)
    t.desenhar(tela)
    assert t.estado == "falha" and "não respondeu" in t.mensagem


def test_muitos_codigos_cabem_na_tela(tela) -> None:
    fonte = FonteFalsa()
    fonte.codigos = {"armazenados": [(f"P0{i:03d}", "x" * 200) for i in range(12)],
                     "pendentes": []}
    t = te.TelaErros(fonte)
    t.abrir()
    t.desenhar(tela)
    assert t._total() == 12 and not _texto_na_tela(tela, (0, 470, 800, 480))
