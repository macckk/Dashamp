"""Testes do formato de viagem e da FonteReplay (F2.3). Rodam no PC e no Eee PC."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from types import MappingProxyType

import pytest

from painel.fontes.base import Leitura
from painel.fontes.replay import FonteReplay
from painel.fontes.simulada import simular
from painel.gravacao import Gravador, ler_metadados, ler_viagem


def _leituras(segundos: float, hz: float = 8) -> list[Leitura]:
    return [Leitura(t, MappingProxyType(v)) for t, v in simular(segundos, hz)]


def _gravar(caminho: Path, leituras: list[Leitura], **meta) -> None:
    with Gravador(str(caminho), meta, intervalo_s=3600) as g:   # um lote só, no fechar
        for leitura in leituras:
            g.gravar(leitura)


def test_grava_e_le_igual(tmp_path: Path) -> None:
    arq = tmp_path / "v.db"
    originais = _leituras(30)
    _gravar(arq, originais, fonte="FonteSimulada", hz=8)
    lidas = list(ler_viagem(str(arq)))
    assert [(o.t, dict(o.valores)) for o in originais] == lidas
    meta = ler_metadados(str(arq))
    assert meta["versao"] == "1" and meta["fonte"] == "FonteSimulada" and meta["hz"] == "8"
    assert meta["leituras"] == "240" and float(meta["duracao_s"]) == pytest.approx(30.0)
    assert "T" in meta["criado_em"] and meta["criado_em"].endswith("+00:00")
    with sqlite3.connect(arq) as db:
        assert db.execute("SELECT count(*) FROM leituras").fetchone()[0] == 240 * 11
        assert db.execute("SELECT unidade FROM canais WHERE nome='velocidade'").fetchone() == ("km/h",)


def test_grava_em_lote(tmp_path: Path) -> None:
    arq = tmp_path / "lote.db"
    g = Gravador(str(arq), intervalo_s=3600)
    for leitura in _leituras(5):
        g.gravar(leitura)
    with sqlite3.connect(arq) as db:              # nada no disco antes do lote
        assert db.execute("SELECT count(*) FROM leituras").fetchone()[0] == 0
    g.fechar()
    assert g.lotes == 1 and len(list(ler_viagem(str(arq)))) == 40


def test_canal_fora_do_catalogo_e_valores_parciais(tmp_path: Path) -> None:
    arq = tmp_path / "p.db"
    _gravar(arq, [Leitura(0.0, {"rpm": 800.0, "pid_extra": 1.5}), Leitura(0.1, {"rpm": 900.0}),
                  Leitura(0.2, {"temp_motor": 40.0})])
    assert list(ler_viagem(str(arq))) == [(0.0, {"rpm": 800.0, "pid_extra": 1.5}),
                                          (0.1, {"rpm": 900.0}), (0.2, {"temp_motor": 40.0})]
    replay = FonteReplay(str(arq), velocidade=100)
    saida: list[Leitura] = []
    replay.assinar(saida.append)
    with replay:
        assert replay.terminou.wait(2)
    # O replay acumula: canal que não veio mantém o último valor.
    assert dict(saida[-1].valores) == {"rpm": 900.0, "pid_extra": 1.5, "temp_motor": 40.0}


def test_versao_desconhecida(tmp_path: Path) -> None:
    arq = tmp_path / "x.db"
    _gravar(arq, _leituras(1))
    with sqlite3.connect(arq) as db:
        db.execute("UPDATE metadados SET valor='99' WHERE chave='versao'")
    with pytest.raises(ValueError, match="versão"):
        list(ler_viagem(str(arq)))


def test_replay_rapido_bate_com_o_original(tmp_path: Path) -> None:
    arq = tmp_path / "r.db"
    originais = _leituras(20)
    _gravar(arq, originais)
    saida: list[Leitura] = []
    replay = FonteReplay(str(arq), velocidade=40)
    replay.assinar(saida.append)
    t0 = time.monotonic()
    with replay:
        assert replay.terminou.wait(5)
    assert 0.3 < time.monotonic() - t0 < 1.5          # 20 s a 40× = 0,5 s
    assert replay.erro is None
    assert [(o.t, dict(o.valores)) for o in originais] == [(s.t, dict(s.valores)) for s in saida]
    assert replay.ultima().t == originais[-1].t


def test_replay_no_ritmo_e_mudando_velocidade(tmp_path: Path) -> None:
    arq = tmp_path / "ritmo.db"
    _gravar(arq, _leituras(4, hz=20))
    replay = FonteReplay(str(arq), velocidade=1)
    t0 = time.monotonic()
    with replay:
        time.sleep(1.0)
        t_dados = replay.ultima().t
        assert 0.8 < t_dados < 1.2                      # 1× : 1 s de viagem em 1 s
        replay.velocidade = 3                           # faltam ~3 s de viagem → ~1 s
        assert replay.terminou.wait(3)
    assert 1.7 < time.monotonic() - t0 < 2.6
    with pytest.raises(ValueError):
        replay.velocidade = 0


def test_replay_repetindo(tmp_path: Path) -> None:
    arq = tmp_path / "rep.db"
    _gravar(arq, _leituras(1))                          # 8 leituras
    replay = FonteReplay(str(arq), velocidade=20, repetir=True)
    with replay:
        time.sleep(0.5)                                 # ~10 voltas de 0,05 s
        assert replay.ativa
    assert replay.leituras > 24 and not replay.ativa


def test_arquivo_que_nao_e_viagem(tmp_path: Path) -> None:
    arq = tmp_path / "nada.db"
    sqlite3.connect(arq).close()
    with pytest.raises(sqlite3.OperationalError):
        FonteReplay(str(arq))
