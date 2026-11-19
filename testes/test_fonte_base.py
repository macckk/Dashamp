"""Testes da interface `Fonte` (F2.1). Rodam no PC e no Eee PC (sem pygame)."""
from __future__ import annotations

import threading
import time
from collections.abc import Mapping

import pytest

from painel.fontes.base import (
    CANAIS, Fonte, FontePeriodica, Leitura, canais_desconhecidos,
)


class Rampa(FontePeriodica):
    def amostrar(self, t: float) -> Mapping[str, float]:
        return {"rpm": 800 + 1000 * t, "velocidade": 10 * t}


class Quebrada(FontePeriodica):
    def amostrar(self, t: float) -> Mapping[str, float]:
        raise ValueError("sensor desligado")


class Empurrada(Fonte):
    """Fonte guiada de fora, como a UDP: publica quando chega um dado."""

    def __init__(self) -> None:
        super().__init__()
        self.chegou = threading.Event()

    def _rodar(self) -> None:
        while not self._parar.is_set():
            if self.chegou.wait(0.05):
                self.chegou.clear()
                self._publicar({"marcha": 3})


def _esperar(cond, limite: float = 2.0) -> bool:
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_catalogo_coerente() -> None:
    for nome in ("rpm", "velocidade", "marcha", "temp_motor", "temp_ar", "acelerador",
                 "tensao", "combustivel_lh"):
        assert nome in CANAIS
    for nome, c in CANAIS.items():
        assert c.nome == nome and c.minimo < c.maximo and c.descricao
    assert CANAIS["rpm"].limitar(12000) == 9000 and CANAIS["velocidade"].limitar(-3) == 0
    assert canais_desconhecidos({"rpm": 1, "rmp": 2}) == ["rmp"]
    with pytest.raises(TypeError):
        CANAIS["novo"] = CANAIS["rpm"]          # catálogo só leitura


def test_sem_leitura_antes_de_iniciar() -> None:
    f = Rampa(10)
    assert f.ultima() is None and not f.ativa
    with pytest.raises(ValueError):
        Rampa(0)


def test_periodica_no_ritmo_e_para() -> None:
    f = Rampa(20)
    f.iniciar()
    time.sleep(1.0)
    f.parar()
    assert not f.ativa and f.erro is None
    assert 17 <= f.leituras <= 23                 # 20 Hz por ~1 s
    n = f.leituras
    time.sleep(0.2)
    assert f.leituras == n                        # parou de verdade
    u = f.ultima()
    assert isinstance(u, Leitura) and 0.8 < u.t < 1.2
    assert u.valores["rpm"] == pytest.approx(800 + 1000 * u.t)
    assert not canais_desconhecidos(u.valores)
    with pytest.raises(TypeError):
        u.valores["rpm"] = 0                      # leitura imutável: o app pode guardá-la


def test_iniciar_duas_vezes_e_reiniciar() -> None:
    f = Rampa(50)
    with f:
        with pytest.raises(RuntimeError):
            f.iniciar()
        assert _esperar(lambda: f.leituras > 0)
    f.iniciar()                                   # depois de parar, recomeça o tempo do zero
    assert _esperar(lambda: f.ultima() is not None and f.ultima().t < 0.5)
    f.parar()


def test_erro_na_thread_fica_registrado() -> None:
    f = Quebrada(10)
    f.iniciar()
    assert _esperar(lambda: not f.ativa)
    assert isinstance(f.erro, ValueError) and f.ultima() is None


def test_fonte_empurrada() -> None:
    with Empurrada() as f:
        assert f.ultima() is None
        f.chegou.set()
        assert _esperar(lambda: f.ultima() is not None)
        assert f.ultima().valores == {"marcha": 3}
    assert not f.ativa


def test_ultima_nao_bloqueia_com_leitor_rapido() -> None:
    """O laço de quadros lê muito mais rápido do que a fonte publica; nada trava."""
    with Rampa(20) as f:
        fim = time.monotonic() + 0.5
        lidas = 0
        while time.monotonic() < fim:
            f.ultima()
            lidas += 1
        assert lidas > 10000 and f.leituras >= 7       # 20 Hz por 0,5 s, mesmo com o leitor
