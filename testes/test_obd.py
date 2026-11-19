"""Testes da FonteOBD (F3.1): agenda por prioridade, PIDs suportados e reconexão.

Usam um adaptador falso (rápidos, rodam no Windows). O teste com o ELM327-emulator de verdade
só roda onde ele está instalado e abre a porta pela rede (no Eee PC).
"""
from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import time
from collections import Counter

import pytest

from painel.fontes import obd as fo
from painel.fontes.base import CANAIS

TODOS = {"RPM": 2000.0, "SPEED": 50.0, "THROTTLE_POS": 20.0, "ENGINE_LOAD": 30.0,
         "INTAKE_PRESSURE": 40.0, "MAF": 5.0, "COOLANT_TEMP": 90.0, "INTAKE_TEMP": 25.0,
         "CONTROL_MODULE_VOLTAGE": 14.1, "FUEL_LEVEL": 60.0, "O2_B1S2": 0.45,
         "SHORT_FUEL_TRIM_1": 1.5, "LONG_FUEL_TRIM_1": -2.0, "ELM_VOLTAGE": 13.9,
         "COMMANDED_EQUIV_RATIO": 1.0}


class Falso:
    """Adaptador falso: `respostas` vazias depois de `cair_em` leituras (carro desligado)."""

    def __init__(self, pids: dict[str, float], situacao: str = "conectado",
                 cair_em: int | None = None, atraso_s: float = 0.002) -> None:
        self.pids, self._situacao, self.cair_em, self.atraso_s = pids, situacao, cair_em, atraso_s
        self.lidos: Counter[str] = Counter()
        self.fechado = False
        self.codigos = {"armazenados": [("P0143", "O2 Sensor Circuit Low Voltage")],
                        "pendentes": [("P0300", "")]}
        self.aceita_apagar = True

    def situacao(self) -> str:
        return self._situacao

    def suporta(self, comando: str) -> bool:
        return comando in self.pids

    def ler(self, comando: str) -> float | None:
        time.sleep(self.atraso_s)                    # o ELM327 leva alguns ms por pergunta
        if self.cair_em is not None and sum(self.lidos.values()) >= self.cair_em:
            return None
        self.lidos[comando] += 1
        return self.pids[comando]

    def erros(self, tipo: str) -> list[tuple[str, str]]:
        return list(self.codigos[tipo])

    def apagar_erros(self) -> bool:
        if self.aceita_apagar:
            self.codigos = {t: [] for t in self.codigos}
        return self.aceita_apagar

    def fechar(self) -> None:
        self.fechado = True


def esperar(condicao, s: float = 3.0) -> bool:
    fim = time.monotonic() + s
    while not condicao() and time.monotonic() < fim:
        time.sleep(0.01)
    return condicao()


def test_agenda_usa_canais_do_catalogo() -> None:
    assert {p.canal for p in fo.AGENDA} <= set(CANAIS)
    rapidos = [p.canal for p in fo.AGENDA if p.intervalo_s == 0]
    assert rapidos == ["rpm", "velocidade"]


def test_agenda_so_com_pids_suportados() -> None:
    pids = {"RPM": 1.0, "SPEED": 1.0, "ELM_VOLTAGE": 12.0, "O2_B1S2": 0.1}
    itens = {i.canal: i.comando for i in fo.montar_agenda(Falso(pids))}
    assert itens == {"rpm": "RPM", "velocidade": "SPEED", "tensao": "ELM_VOLTAGE",
                     "sonda_o2": "O2_B1S2"}               # cai para o 2.º comando da lista


def test_prioridade_rapidos_em_todo_ciclo() -> None:
    falso = Falso(TODOS)
    fonte = fo.FonteOBD(conectar=lambda p, b: falso)
    with fonte:
        time.sleep(1.5)
    assert fonte.erro is None and fonte.situacao == "conectado"
    rpm, temp = falso.lidos["RPM"], falso.lidos["COOLANT_TEMP"]
    assert falso.lidos["SPEED"] == pytest.approx(rpm, abs=1)
    assert 1 <= temp <= 2                                    # 1 Hz
    assert 4 <= falso.lidos["THROTTLE_POS"] <= 7               # 4 Hz
    assert rpm > 10 * temp and rpm <= 1.5 * fo.CICLOS_MAX_HZ + 1   # teto de ciclos
    v = fonte.ultima().valores
    assert v["temp_motor"] == 90 and v["tensao"] == 14.1 and v["trim_longo"] == -2.0
    assert set(fonte.canais) == {p.canal for p in fo.AGENDA} - {"combustivel_lh"}  # sem PID 5E
    assert fonte.taxa_rpm > 10


def test_reconecta_e_zera_quando_o_carro_some() -> None:
    conexoes = iter([
        RuntimeError("sem porta"),                            # adaptador ainda não ligado
        Falso(TODOS, situacao="sem_carro"),                   # ignição desligada
        Falso(TODOS, cair_em=30),                             # liga e depois cai
        Falso({**TODOS, "RPM": 3000.0}),                      # volta
    ])
    criadas: list[Falso] = []

    def conectar(porta, baud):
        c = next(conexoes)
        if isinstance(c, Exception):
            raise c
        criadas.append(c)
        return c

    fonte = fo.FonteOBD("socket://x:1", 38400, conectar=conectar, intervalo_reconexao_s=0.05)
    zerados = []
    fonte.assinar(lambda l: zerados.append(l) if l.valores.get("rpm") == 0 else None)
    with fonte:
        assert esperar(lambda: (fonte.ultima() is not None
                                and fonte.ultima().valores["rpm"] == 3000))
    assert fonte.erro is None
    assert fonte.contagem["falha_conexao"] == 2 and fonte.contagem["reconexao"] == 1
    assert fonte.contagem["sem_resposta"] == 1
    assert zerados and zerados[0].valores["velocidade"] == 0
    assert zerados[0].valores["temp_motor"] == 90                # repouso mantém a temperatura
    assert all(c.fechado for c in criadas[:2])


def test_sem_rpm_nem_velocidade_e_sem_carro() -> None:
    falso = Falso({"ELM_VOLTAGE": 12.5})
    fonte = fo.FonteOBD(conectar=lambda p, b: falso, intervalo_reconexao_s=0.05)
    with fonte:
        assert esperar(lambda: fonte.contagem["reconexao"] >= 1)
        assert fonte.situacao in ("sem_carro", "conectando")
    assert fonte.ultima() is None


# --- com o ELM327-emulator de verdade -------------------------------------------------------


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(sys.platform == "win32" or importlib.util.find_spec("elm") is None
                    or importlib.util.find_spec("obd") is None,
                    reason="o ELM327-emulator pela rede só funciona no Linux (Eee PC)")
def test_emulador_e_reinicio(tmp_path) -> None:
    porta = _porta_livre()

    def emulador() -> subprocess.Popen:
        return subprocess.Popen([sys.executable, "scripts/emulador_obd.py", "--erros",
                                 "P0143,P0300", "--pendentes", "C0035", "--", "-s", "car",
                                 "-n", str(porta), "-b", str(tmp_path / "elm.txt")],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    emu = emulador()
    fonte = fo.FonteOBD(f"socket://127.0.0.1:{porta}", 38400, intervalo_reconexao_s=1.0)
    try:
        with fonte:
            assert esperar(lambda: fonte.contagem["ciclos"] >= 10, 60), dict(fonte.contagem)
            assert {"rpm", "velocidade", "temp_motor", "tensao"} <= set(fonte.canais)
            codigos = fonte.ler_erros().result(20)
            assert [c for c, _ in codigos["armazenados"]] == ["P0143", "P0300"]
            assert [c for c, _ in codigos["pendentes"]] == ["C0035"]
            assert "Misfire" in codigos["armazenados"][1][1]
            assert fonte.apagar_erros().result(20) is True
            assert fonte.ler_erros().result(20) == {"armazenados": [], "pendentes": []}
            assert fonte.ultima().valores["combustivel_lh"] >= 0          # pelo MAF
            emu.terminate()
            emu.wait(10)
            assert esperar(lambda: fonte.contagem["reconexao"] >= 1, 30), dict(fonte.contagem)
            antes = fonte.contagem["ciclos"]
            emu = emulador()
            assert esperar(lambda: fonte.contagem["ciclos"] > antes + 10, 60), \
                dict(fonte.contagem)
        assert fonte.erro is None
    finally:
        emu.terminate()
        emu.wait(10)


def test_consumo_publicado_pelo_maf() -> None:
    falso = Falso(TODOS)                           # MAF 5 g/s, 50 km/h, λ 1,0
    fonte = fo.FonteOBD(conectar=lambda p, b: falso, combustivel="gasolina")
    with fonte:
        assert esperar(lambda: fonte.contagem["ciclos"] >= 10)
    v = fonte.ultima().valores
    assert fonte.consumo.metodo == "maf"
    assert v["combustivel_lh"] == pytest.approx(5 / 14.7 * 3600 / 745)     # 1,644 L/h
    assert v["consumo_kml"] == pytest.approx(50 / v["combustivel_lh"])
    assert "consumo_medio_kml" not in v or v["consumo_medio_kml"] > 0


def test_consumo_pelo_pid_5e_quando_existe() -> None:
    falso = Falso({**TODOS, "FUEL_RATE": 7.5})
    fonte = fo.FonteOBD(conectar=lambda p, b: falso)
    with fonte:
        assert esperar(lambda: fonte.contagem["ciclos"] >= 3
                       and falso.lidos["FUEL_RATE"] >= 1)
    assert fonte.consumo.metodo == "pid"
    assert fonte.ultima().valores["combustivel_lh"] == 7.5


def test_ler_e_apagar_codigos_pela_thread() -> None:
    falso = Falso(TODOS)
    fonte = fo.FonteOBD(conectar=lambda p, b: falso)
    with fonte:
        assert esperar(lambda: fonte.situacao == "conectado")
        codigos = fonte.ler_erros().result(2)
        assert codigos == {"armazenados": [("P0143", "O2 Sensor Circuit Low Voltage")],
                           "pendentes": [("P0300", "")]}
        falso.aceita_apagar = False                 # motor ligado: a central recusa
        assert fonte.apagar_erros().result(2) is False
        falso.aceita_apagar = True
        assert fonte.apagar_erros().result(2) is True
        assert fonte.ler_erros().result(2) == {"armazenados": [], "pendentes": []}
    assert fonte.erro is None


def test_pedido_sem_carro_falha_na_hora() -> None:
    fonte = fo.FonteOBD(conectar=lambda p, b: Falso(TODOS, situacao="sem_carro"),
                        intervalo_reconexao_s=0.05)
    f = fonte.ler_erros()                           # nem iniciada
    with pytest.raises(fo.SemConexao):
        f.result(1)
    with fonte:
        assert esperar(lambda: fonte.contagem["falha_conexao"] >= 1)
        with pytest.raises(fo.SemConexao):
            fonte.apagar_erros().result(1)


def test_pedido_pendente_recebe_erro_quando_a_conexao_cai() -> None:
    falso = Falso(TODOS, cair_em=40, atraso_s=0.01)
    fonte = fo.FonteOBD(conectar=lambda p, b: falso, intervalo_reconexao_s=5)
    with fonte:
        assert esperar(lambda: fonte.situacao == "conectado")
        falso.erros = lambda tipo: (_ for _ in ()).throw(fo.SemConexao("sem resposta"))
        with pytest.raises(fo.SemConexao):
            fonte.ler_erros().result(3)
