"""Testes do diagnóstico OBD-II (preparação da F3.3), com o adaptador falso de test_obd."""
from __future__ import annotations

import pygame
import pytest

from carputer import diagnostico as dg
from core.app import ATALHOS_APP
from testes.test_obd import TODOS, Falso

VIN = "9BWZZZ000VT000000"            # VIN fictício (zeros), só o formato é real


class FalsoCompleto(Falso):
    protocolo = "ISO 15765-4 (CAN 11/500)"

    def suportados(self) -> list[tuple[str, str]]:
        return [(n, f"descrição de {n}") for n in self.pids if n != "ELM_VOLTAGE"]

    def consultar_texto(self, comando: str) -> str | None:
        extras = {"VIN": VIN, "ELM_VERSION": "ELM327 v1.5", "FUEL_TYPE": "Bifuel running Ethanol",
                  "STATUS": "luz da injeção apagada, 0 código(s)", "OBD_COMPLIANCE": None,
                  "ELM_VOLTAGE": "13.9 V"}
        if comando in extras:
            return extras[comando]
        v = self.ler(comando)
        return None if v is None else f"{v:g}"


def test_ano_do_vin() -> None:
    assert dg.ano_do_vin(VIN, 2025) == 1997                 # 'V' = 1997 ou 2027
    assert dg.ano_do_vin(VIN, 2026) == 2027                 # ano-modelo pode ser o seguinte
    assert dg.ano_do_vin("9BW000000E0000000", 2026) == 2014   # 'E'
    assert dg.ano_do_vin("curto") is None


def test_vin_nunca_inteiro() -> None:
    r = dg.vin_resumido(VIN)
    assert VIN not in r and "9BW" in r and "omitido" in r
    assert dg.vin_resumido(None) == "não informado"


def test_relatorio_completo(tmp_path) -> None:
    avisos: list[str] = []
    rel = dg.diagnosticar("/dev/ttyUSB0", 38400, avisos.append,
                          conectar=lambda p, b: FalsoCompleto(TODOS),
                          segundos_rpm=0.3, segundos_painel=0.5)
    assert "ISO 15765-4" in rel and "ELM327 v1.5" in rel and "Bifuel" in rel
    assert VIN not in rel and "fabricante 9BW" in rel
    assert f"## PIDs suportados ({len(TODOS) - 1})" in rel
    assert "| `RPM` | descrição de RPM | 2000 |" in rel
    assert "Só o rpm: **" in rel and "Painel: **" in rel and "Consumo calculado por: maf" in rel
    assert "Armazenados: `P0143` O2 Sensor Circuit Low Voltage" in rel
    assert "Pendentes: `P0300`" in rel
    assert avisos[0].startswith("Procurando") and avisos[-1] == "Pronto."
    caminho = dg.salvar(rel, str(tmp_path / "diag"))
    assert open(caminho, encoding="utf-8").read() == rel


def test_sem_carro_desiste_com_relatorio(monkeypatch) -> None:
    rel = dg.diagnosticar(None, None, lambda s: None,
                          conectar=lambda p, b: FalsoCompleto(TODOS, situacao="sem_carro"),
                          espera_adaptador_s=0.0)
    assert "**Falhou**: sem_carro" in rel


def test_porta_inexistente(monkeypatch) -> None:
    def conectar(p, b):
        raise OSError("could not open port /dev/ttyUSB0")
    rel = dg.diagnosticar("/dev/ttyUSB0", None, lambda s: None, conectar=conectar,
                          espera_adaptador_s=0.0)
    assert "**Falhou**: sem_adaptador (could not open port" in rel


def test_teclas_do_carro() -> None:
    assert ATALHOS_APP[pygame.K_F4] == "painel --obd"
    assert ATALHOS_APP[pygame.K_F5] == "diagnostico"
