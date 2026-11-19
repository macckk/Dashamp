"""Testes dos widgets (F2.4), com o display "dummy" do SDL (rodam no PC e no Eee PC)."""
from __future__ import annotations

import math
import os
from types import SimpleNamespace

import pygame
import pytest

from painel.widgets import Barra, Digitos, Historico, LuzEspia, Painel, Ponteiro, Zona

VERMELHO, AZUL = (230, 40, 30), (60, 140, 255)


def _tem_cor(tela: pygame.Surface, ret: pygame.Rect, cor: tuple[int, int, int],
             tolerancia: int = 30) -> bool:
    """Há algum pixel perto da cor? (os glifos são antisserrilhados: a cor exata pode faltar)"""
    for x in range(ret.x, ret.right):
        for y in range(ret.y, ret.bottom):
            p = tela.get_at((x, y))
            if all(abs(p[i] - cor[i]) <= tolerancia for i in range(3)):
                return True
    return False


@pytest.fixture(autouse=True)
def tela():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    t = pygame.display.set_mode((800, 480))
    yield t
    pygame.display.quit()


def test_interpolacao_exponencial_e_zonas() -> None:
    b = Barra("rpm", (0, 0, 100, 10), 0, 100, tau=0.2, zonas=[Zona(80, 100, VERMELHO)])
    b.atualizar(None, 0.1)
    assert b.valor is None                         # sem dado: não inventa valor
    b.atualizar(0, 0.03)
    assert b.valor == 0                            # primeiro valor: vai direto
    b.atualizar(100, 0.2)                          # um tau: 63% do caminho
    assert b.valor == pytest.approx(100 * (1 - math.exp(-1)))
    for _ in range(100):
        b.atualizar(100, 0.033)
    assert b.valor == pytest.approx(100, abs=0.01) and b.zona() == Zona(80, 100, VERMELHO)
    assert b.fracao(150) == 1.0 and b.fracao(-5) == 0.0
    sem = Barra("x", (0, 0, 10, 10), 0, 1, tau=0)
    sem.atualizar(0.5, 0.033)
    assert sem.valor == 0.5
    with pytest.raises(ValueError):
        Barra("x", (0, 0, 10, 10), 5, 5)


def test_ponteiro_angulos_e_cache_sob_demanda(tela) -> None:
    p = Ponteiro("rpm", (200, 200), 150, 0, 8000)
    assert p.angulo(0) == 225 and p.angulo(8000) == -45 and p.angulo(4000) == 90
    assert not p.cache.quadros                     # nada pré-gerado: carga instantânea
    fundo = pygame.Surface((800, 480))
    p.pintar_fundo(fundo)
    for v in (0, 1000, 1000, 8000):
        p.atualizar(v, 1.0)
        p.desenhar(tela, fundo)
    assert len(p.cache.quadros) == 3
    p.atualizar(8000, 1.0)
    assert p.desenhar(tela, fundo) == []           # mesmo ângulo: não redesenha
    # A ponta do ponteiro em 90° (4000 rpm) fica acima do centro, na cor do ponteiro.
    p.atualizar(4000, 0)
    p.tau = 0
    p.atualizar(4000, 0.033)
    p.desenhar(tela, fundo)
    cor = tela.get_at((200, 200 - int(150 * 0.7)))[:3]
    assert cor[0] > 180 and cor[1] < 80


def test_barra_segmentos_e_cores(tela) -> None:
    b = Barra("temp_motor", (10, 10, 210, 20), 0, 100, segmentos=10, espaco=2, tau=0,
              zonas=[Zona(0, 30, AZUL), Zona(80, 100, VERMELHO)], cor=(0, 200, 0),
              cor_apagada=(20, 20, 20))
    fundo = pygame.Surface((800, 480))
    b.pintar_fundo(fundo)
    b.atualizar(85, 0.033)
    assert b.acesos() == 8 or b.acesos() == 9      # round(8,5)
    b.atualizar(50, 0.033)
    assert b.acesos() == 5
    assert b.desenhar(tela, fundo) == [pygame.Rect(10, 10, 210, 20)]
    meio = lambda i: (10 + i * 21 + 9, 20)        # noqa: E731  (centro do segmento i)
    assert tela.get_at(meio(0))[:3] == AZUL
    assert tela.get_at(meio(4))[:3] == (0, 200, 0)
    assert tela.get_at(meio(5))[:3] == (20, 20, 20)  # apagado
    v = Barra("acelerador", (0, 0, 10, 100), 0, 100, segmentos=4, vertical=True, tau=0,
              espaco=0)
    v.pintar_fundo(fundo)
    v.atualizar(50, 0.033)
    v.desenhar(tela, fundo)
    assert tela.get_at((5, 90))[:3] != tela.get_at((5, 10))[:3]  # enche de baixo para cima


def test_digitos_texto() -> None:
    d = Digitos("velocidade", (0, 0), 3, 40, 0, 260, tau=0)
    assert d.texto() == "---"
    assert d.texto(13.4) == " 13" and d.texto(0) == "  0" and d.texto(999) == "260"
    assert Digitos("tensao", (0, 0), 3, 40, 0, 18, casas=1).texto(14.13) == "141"
    assert Digitos("x", (0, 0), 2, 40, -99, 999).texto(-150) == "--"   # não cabe


def test_digitos_desenha_e_muda_de_cor(tela) -> None:
    d = Digitos("rpm", (100, 100), 2, 60, 0, 99, tau=0, cor=(0, 255, 0),
                zonas=[Zona(90, 99, VERMELHO)], cor_apagada=(10, 10, 10))
    fundo = pygame.Surface((800, 480))
    d.pintar_fundo(fundo)
    d.atualizar(88, 0.033)
    d.desenhar(tela, fundo)
    assert _tem_cor(tela, d.ret, (0, 255, 0)) and not _tem_cor(tela, d.ret, VERMELHO)
    d.atualizar(95, 0.033)
    assert d.desenhar(tela, fundo)                 # cor mudou (zona): redesenha
    assert _tem_cor(tela, d.ret, VERMELHO) and not _tem_cor(tela, d.ret, (0, 255, 0))


def test_luz_acende_na_zona_e_pisca() -> None:
    luz = LuzEspia("rpm", (50, 50), 10, [Zona(5000, 9000, VERMELHO)], piscar_hz=2)
    luz.atualizar(3000, 0.01)
    assert not luz.acesa()
    luz.atualizar(6000, 0.01)
    estados = []
    for _ in range(40):                            # 1 s a 40 Hz: 2 ciclos de pisca
        luz.atualizar(6000, 0.025)
        estados.append(luz.acesa())
    assert 15 <= sum(estados) <= 25 and sum(a != b for a, b in zip(estados, estados[1:])) >= 3
    with pytest.raises(ValueError):
        LuzEspia("x", (0, 0), 5, [])


def test_historico_amostra_na_taxa(tela) -> None:
    h = Historico("velocidade", (0, 0, 200, 50), 0, 100, segundos=10, taxa=4, tau=0)
    fundo = pygame.Surface((800, 480))
    h.pintar_fundo(fundo)
    for i in range(30 * 3):                        # 3 s a 30 fps
        h.atualizar(i, 1 / 30)
    assert 11 <= len(h.amostras) <= 12
    assert h.desenhar(tela, fundo) and h.desenhar(tela, fundo) == []
    for _ in range(30 * 20):
        h.atualizar(50, 1 / 30)
    assert len(h.amostras) == 40                   # 10 s × 4/s, janela deslizante


def test_painel_agrupa_sobrepostos_e_redesenha_so_o_que_muda(tela) -> None:
    ponteiro = Ponteiro("rpm", (200, 240), 180, 0, 8000, tau=0)
    marcha = Digitos("marcha", (185, 320), 1, 50, 0, 6, tau=0, cor=(0, 0, 255),
                     cor_apagada=(200, 200, 200))
    barra = Barra("acelerador", (450, 100, 300, 20), 0, 100, tau=0)
    painel = Painel((800, 480), [ponteiro, marcha, barra])
    assert [len(g) for g in painel.grupos] == [2, 1]
    fonte = SimpleNamespace(ultima=lambda: SimpleNamespace(
        valores={"rpm": 1000, "marcha": 2, "acelerador": 50}))
    painel.atualizar(fonte, 0.033)
    assert painel.desenhar(tela) is None           # primeiro quadro: tela inteira
    assert painel.desenhar(tela) == []             # nada mudou
    fonte.ultima = lambda: SimpleNamespace(valores={"rpm": 3000, "marcha": 2, "acelerador": 50})
    painel.atualizar(fonte, 0.033)
    sujos = painel.desenhar(tela)
    assert sujos == [ponteiro.ret.union(marcha.ret)]
    # A marcha continua desenhada depois de o grupo ser restaurado por causa do ponteiro.
    assert _tem_cor(tela, marcha.ret, (0, 0, 255), tolerancia=10)
