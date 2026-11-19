"""Fonte OBD-II (F3.1): lê o carro por um adaptador ELM327 com o python-OBD.

**Agendador por prioridade.** A porta do ELM327 atende uma pergunta por vez (~10 a 20 por segundo
num carro de verdade), então cada canal tem um intervalo: `rpm` e `velocidade` são lidos em todo
ciclo; acelerador, carga, pressão do coletor e MAF a cada 0,25–0,5 s; temperaturas, tensão,
tanque, sonda e trims a 1 s. Em cada ciclo vão os rápidos e **um** lento (o mais atrasado), para
que os lentos nunca derrubem a taxa do rpm. A leitura é publicada no fim de cada ciclo, e o ciclo
tem teto de `CICLOS_MAX_HZ` (15/s).

**PIDs suportados.** Na conexão o python-OBD pergunta ao carro quais PIDs ele tem; canais sem PID
suportado saem da agenda (a tensão cai para a leitura do próprio ELM327, `AT RV`, que todo
adaptador tem).

**Reconexão.** Sem adaptador, sem ignição ou com 5 respostas vazias seguidas do rpm, a fonte
publica `REPOUSO` (os ponteiros descem), fecha a porta e tenta de novo a cada 3 s.

Por que não `obd.Async`: ele lê todos os comandos observados em sequência, sem prioridade; a thread
da `Fonte` já é o laço assíncrono, e o agendador fica nela.

O `import obd` (que carrega o pint) leva ~4 s no Eee PC: ele é feito dentro da thread, para o
painel abrir na hora.

    python -m painel.fontes.obd [--porta /dev/ttyUSB0 | socket://host:35000] [--baud 38400]
"""
from __future__ import annotations

import argparse
import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from painel.fontes.base import REPOUSO, Fonte

INTERVALO_RECONEXAO_S = 3.0
FALHAS_PARA_RECONECTAR = 5
# Teto de ciclos por segundo. Um ELM327 de verdade fica abaixo disso (cada pergunta leva dezenas de
# ms); com o emulador, que responde na hora, o laço sem teto tomava 60% da CPU do Eee PC (cada
# resposta passa pelo pint) e o painel caía para 25 fps.
CICLOS_MAX_HZ = 15.0


@dataclass(frozen=True)
class PidCanal:
    canal: str
    comandos: tuple[str, ...]        # nomes do python-OBD; vale o primeiro suportado
    intervalo_s: float               # 0 = em todo ciclo


AGENDA: tuple[PidCanal, ...] = (
    PidCanal("rpm", ("RPM",), 0.0),
    PidCanal("velocidade", ("SPEED",), 0.0),
    PidCanal("acelerador", ("THROTTLE_POS",), 0.25),
    PidCanal("carga", ("ENGINE_LOAD",), 0.5),
    PidCanal("pressao_coletor", ("INTAKE_PRESSURE",), 0.5),
    PidCanal("maf", ("MAF",), 0.5),
    PidCanal("temp_motor", ("COOLANT_TEMP",), 1.0),
    PidCanal("temp_ar", ("INTAKE_TEMP",), 1.0),
    PidCanal("tensao", ("CONTROL_MODULE_VOLTAGE", "ELM_VOLTAGE"), 1.0),
    PidCanal("combustivel_nivel", ("FUEL_LEVEL",), 1.0),
    PidCanal("sonda_o2", ("O2_B1S1", "O2_B1S2"), 1.0),
    PidCanal("trim_curto", ("SHORT_FUEL_TRIM_1",), 1.0),
    PidCanal("trim_longo", ("LONG_FUEL_TRIM_1",), 1.0),
)


class Conexao(Protocol):
    """O que a fonte usa do adaptador (o python-OBD de verdade ou um falso nos testes)."""

    def situacao(self) -> str: ...          # "sem_adaptador" | "sem_carro" | "conectado"
    def suporta(self, comando: str) -> bool: ...
    def ler(self, comando: str) -> float | None: ...
    def fechar(self) -> None: ...


class ConexaoPythonOBD:
    def __init__(self, porta: str | None, baudrate: int | None, timeout: float = 0.5) -> None:
        import obd  # noqa: PLC0415 — lento (pint); só na thread da fonte

        obd.logger.setLevel(logging.ERROR)    # sem "Query failed" a cada pergunta (flash)
        self._obd = obd
        self._c = obd.OBD(porta, baudrate=baudrate, fast=False, timeout=timeout)
        self.protocolo = self._c.protocol_name()

    def situacao(self) -> str:
        s = self._c.status()
        if s == self._obd.OBDStatus.CAR_CONNECTED:
            return "conectado"
        return "sem_adaptador" if s == self._obd.OBDStatus.NOT_CONNECTED else "sem_carro"

    def suporta(self, comando: str) -> bool:
        return self._obd.commands.has_name(comando) and self._c.supports(
            self._obd.commands[comando])

    def ler(self, comando: str) -> float | None:
        r = self._c.query(self._obd.commands[comando])
        if r.is_null():
            return None
        v = r.value
        return float(getattr(v, "magnitude", v))

    def fechar(self) -> None:
        self._c.close()


FabricaConexao = Callable[[str | None, int | None], Conexao]


class _Item:
    __slots__ = ("canal", "comando", "intervalo", "proximo")

    def __init__(self, canal: str, comando: str, intervalo: float) -> None:
        self.canal, self.comando, self.intervalo = canal, comando, intervalo
        self.proximo = 0.0


def montar_agenda(conexao: Conexao, agenda: Sequence[PidCanal] = AGENDA) -> list[_Item]:
    """Um item por canal com algum comando suportado (o primeiro da lista que o carro tiver)."""
    itens = []
    for p in agenda:
        for comando in p.comandos:
            if conexao.suporta(comando):
                itens.append(_Item(p.canal, comando, p.intervalo_s))
                break
    return itens


class FonteOBD(Fonte):
    """`porta`: None = procurar (USB/Bluetooth), "/dev/ttyUSB0", "/dev/rfcomm0" ou
    "socket://host:porta" (emulador pela rede). `conectar` troca o python-OBD nos testes."""

    def __init__(self, porta: str | None = None, baudrate: int | None = None,
                 conectar: FabricaConexao | None = None,
                 intervalo_reconexao_s: float = INTERVALO_RECONEXAO_S) -> None:
        super().__init__()
        self.porta, self.baudrate = porta, baudrate
        self._conectar = conectar or ConexaoPythonOBD
        self.intervalo_reconexao_s = intervalo_reconexao_s
        self.situacao = "iniciando"          # para a caixa de espera do painel
        self.canais: list[str] = []          # canais que o carro suporta
        self.contagem: Counter[str] = Counter()
        self._rpm_lidos = 0
        self._t_conexao = 0.0

    @property
    def taxa_rpm(self) -> float:
        """Leituras de rpm por segundo desde a última conexão."""
        dt = time.monotonic() - self._t_conexao
        return self._rpm_lidos / dt if self._t_conexao and dt > 0 else 0.0

    def _rodar(self) -> None:
        while not self._parar.is_set():
            conexao = self._abrir()
            if conexao is None:
                self._parar.wait(self.intervalo_reconexao_s)
                continue
            try:
                self._ler_ate_cair(conexao)
            finally:
                conexao.fechar()
            if self._ultima is not None:
                self._publicar({**self._ultima.valores, **REPOUSO})
            if not self._parar.is_set():
                self.contagem["reconexao"] += 1
                self._parar.wait(self.intervalo_reconexao_s)

    def _abrir(self) -> Conexao | None:
        self.situacao = "conectando"
        try:
            conexao = self._conectar(self.porta, self.baudrate)
        except Exception:  # noqa: BLE001 — porta inexistente, permissão, adaptador mudo
            self.contagem["falha_conexao"] += 1
            self.situacao = "sem_adaptador"
            return None
        situacao = conexao.situacao()
        if situacao != "conectado":
            self.contagem["falha_conexao"] += 1
            self.situacao = situacao
            conexao.fechar()
            return None
        return conexao

    def _ler_ate_cair(self, conexao: Conexao) -> None:
        agenda = montar_agenda(conexao)
        self.canais = [i.canal for i in agenda]
        rapidos = [i for i in agenda if i.intervalo <= 0]
        lentos = [i for i in agenda if i.intervalo > 0]
        if not rapidos:
            self.situacao = "sem_carro"
            return
        self.situacao = "conectado"
        self._rpm_lidos, self._t_conexao = 0, time.monotonic()
        estado: dict[str, float] = dict(self._ultima.valores) if self._ultima else {}
        falhas = 0
        periodo = 1.0 / CICLOS_MAX_HZ
        proximo_ciclo = time.monotonic()
        while not self._parar.is_set():
            espera = proximo_ciclo - time.monotonic()
            if espera > 0 and self._parar.wait(espera):
                break
            proximo_ciclo = max(proximo_ciclo + periodo, time.monotonic())
            vazio = False
            for item in rapidos:
                v = conexao.ler(item.comando)
                if v is None:
                    vazio = True
                    continue
                estado[item.canal] = v
                if item.canal == "rpm":
                    self._rpm_lidos += 1
            agora = time.monotonic()
            atrasados = [i for i in lentos if i.proximo <= agora]
            if atrasados:
                item = min(atrasados, key=lambda i: i.proximo)
                item.proximo = agora + item.intervalo
                v = conexao.ler(item.comando)
                if v is not None:
                    estado[item.canal] = v
            falhas = falhas + 1 if vazio else 0
            if falhas >= FALHAS_PARA_RECONECTAR:
                self.contagem["sem_resposta"] += 1
                self.situacao = "conectando"
                return
            if not vazio:
                self.contagem["ciclos"] += 1
                self._publicar(estado)


def main() -> None:
    p = argparse.ArgumentParser(description="Lê o carro (ou o emulador) e imprime os valores.")
    p.add_argument("--porta", help="padrão: procurar")
    p.add_argument("--baud", type=int)
    p.add_argument("--segundos", type=float, default=0)
    a = p.parse_args()
    fonte = FonteOBD(a.porta, a.baud)
    fonte.iniciar()
    t0 = time.monotonic()
    try:
        while not a.segundos or time.monotonic() - t0 < a.segundos:
            time.sleep(1)
            u = fonte.ultima()
            print(f"{fonte.situacao} rpm/s={fonte.taxa_rpm:4.1f}", dict(fonte.contagem),
                  {k: round(v, 1) for k, v in u.valores.items()} if u else "", flush=True)
    except KeyboardInterrupt:
        pass
    fonte.parar()
    if fonte.erro:
        print(f"erro: {fonte.erro!r}")


if __name__ == "__main__":
    main()
