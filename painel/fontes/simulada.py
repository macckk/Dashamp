"""Fonte simulada (F2.2): um carro de passeio com motorista automático, a 8 Hz.

O modelo é de propósito simples (o objetivo é alimentar os mostradores com curvas plausíveis,
não simular um motor):
- motorista em fases: parado em marcha lenta → acelera até uma velocidade-alvo → mantém →
  desacelera (às vezes até parar, às vezes até um alvo menor) → ...; alvos sorteados com semente
  fixa, então a mesma semente dá a mesma viagem;
- câmbio de 5 marchas: rpm = velocidade × razão da marcha; sobe de marcha num ponto que depende do
  acelerador (2500–4500 rpm) e reduz abaixo de ~1300 rpm; cada troca corta o acelerador por 0,4 s;
  saindo da imobilidade a embreagem patina (rpm acima do que a roda pede) até ~10 km/h;
- motor frio (marcha lenta mais alta) que aquece conforme a carga até a válvula termostática
  (~90 °C); ar de admissão esquenta parado e esfria andando;
- consumo proporcional a rpm × carga; tensão de carga do alternador; tanque descendo devagar.

    python -m painel.fontes.simulada --segundos 60 --csv /tmp/simulada.csv

grava em tempo real (pela thread, a 8 Hz) e imprime o ritmo obtido e a CPU usada.
"""
from __future__ import annotations

import argparse
import math
import random
import time
from collections.abc import Mapping

from painel.fontes.base import CANAIS, FontePeriodica

HZ = 8
# km/h a 1000 rpm em cada marcha (1ª..5ª): rpm = velocidade × 1000 / KMH_POR_1000[marcha].
KMH_POR_1000 = (0.0, 8.0, 14.0, 21.0, 28.0, 35.0)
ACEL_MAX = (0.0, 3.2, 2.4, 1.7, 1.2, 0.9)   # m/s² com acelerador a fundo, por marcha
MARCHA_LENTA_QUENTE, MARCHA_LENTA_FRIA = 820.0, 1150.0
RPM_REDUZ = 1300.0
RPM_MAX = 6500.0
TROCA_S = 0.4
TEMP_TERMOSTATO = 90.0


class Carro:
    """Estado da simulação. `passo(dt)` avança o tempo; `valores()` lê os canais."""

    def __init__(self, semente: int = 1, temp_inicial: float = 25.0) -> None:
        self.rng = random.Random(semente)
        self.v = 0.0                       # m/s
        self.marcha = 0
        self.rpm = MARCHA_LENTA_FRIA
        self.acelerador = 0.0              # 0..1
        self.temp_motor = temp_inicial
        self.temp_ambiente = temp_inicial
        self.temp_ar = temp_inicial
        self.combustivel_nivel = 62.0
        self._troca = 0.0                  # tempo restante da troca de marcha em curso
        self._fase = "parado"
        self._fase_t = 0.0
        self._fase_dur = self.rng.uniform(3, 6)
        self._alvo = 0.0                   # km/h
        self._pedal = 0.0                  # acelerador usado na fase "acelera"

    # --- motorista ------------------------------------------------------------

    def _proxima_fase(self) -> None:
        r = self.rng
        kmh = self.v * 3.6
        if self._fase == "parado":
            self._fase, self._alvo = "acelera", r.choice((40, 50, 60, 80, 100, 120))
            self._pedal = r.uniform(0.45, 0.95)
        elif self._fase == "acelera":
            self._fase, self._fase_dur = "mantem", r.uniform(5, 12)
        elif self._fase == "mantem":
            menores = [x for x in (30, 40, 50, 60, 80) if x < kmh - 15]
            self._fase = "freia"
            self._alvo = r.choice(menores) if menores and r.random() < 0.5 else 0.0
        elif self._fase == "freia":
            if self._alvo == 0.0:
                self._fase, self._fase_dur = "parado", r.uniform(4, 8)
            else:
                self._fase, self._fase_dur = "mantem", r.uniform(4, 8)
        self._fase_t = 0.0

    def _dirigir(self, dt: float) -> float:
        """Devolve a aceleração pedida pelo freio (m/s², ≤ 0) e ajusta o acelerador."""
        self._fase_t += dt
        kmh = self.v * 3.6
        freio = 0.0
        if self._fase == "parado":
            self.acelerador = 0.0
            if self._fase_t >= self._fase_dur:
                self._proxima_fase()
        elif self._fase == "acelera":
            self.acelerador = self._pedal
            if kmh >= self._alvo:
                self._proxima_fase()
        elif self._fase == "mantem":
            # Pedal proporcional ao erro + o necessário para vencer o arrasto.
            erro = self._alvo - kmh
            self.acelerador = min(1.0, max(0.0, 0.12 + 0.004 * kmh + 0.05 * erro))
            if self._fase_t >= self._fase_dur:
                self._proxima_fase()
        else:  # freia
            self.acelerador = 0.0
            freio = -2.2 if self._alvo == 0.0 else -1.5
            if kmh <= self._alvo + 0.5:
                if self._alvo == 0.0:
                    self.v = 0.0
                self._proxima_fase()
        return freio

    # --- motor e câmbio ----------------------------------------------------------

    def _marcha_lenta(self) -> float:
        frio = min(1.0, max(0.0, (70.0 - self.temp_motor) / 45.0))
        return MARCHA_LENTA_QUENTE + (MARCHA_LENTA_FRIA - MARCHA_LENTA_QUENTE) * frio

    def _rpm_da_roda(self, marcha: int) -> float:
        return self.v * 3.6 * 1000.0 / KMH_POR_1000[marcha] if marcha else 0.0

    def _cambio(self, dt: float) -> None:
        if self._troca > 0:
            self._troca -= dt
            return
        kmh = self.v * 3.6
        if self.marcha == 0:
            if self.acelerador > 0:
                self.marcha = 1
            return
        if kmh < 1.0 and self.acelerador == 0.0:
            self.marcha = 0
            return
        ponto = 2500.0 + 2000.0 * self.acelerador
        if self.marcha < 5 and self._rpm_da_roda(self.marcha) > ponto:
            self.marcha += 1
            self._troca = TROCA_S
        elif self.marcha > 1 and self._rpm_da_roda(self.marcha) < RPM_REDUZ:
            self.marcha -= 1
            self._troca = TROCA_S

    def passo(self, dt: float) -> None:
        if dt <= 0:
            return
        freio = self._dirigir(dt)
        self._cambio(dt)
        trocando = self._troca > 0
        pedal = 0.0 if trocando else self.acelerador

        # Velocidade: força do motor na marcha - arrasto (ar + rolamento) + freio.
        forca = pedal * ACEL_MAX[self.marcha] if self.marcha else 0.0
        if self.rpm >= RPM_MAX:
            forca = 0.0
        arrasto = 0.00035 * self.v * self.v + (0.12 if self.v > 0 else 0.0)
        self.v = max(0.0, self.v + (forca - arrasto + freio) * dt)

        # Rotação: segue a roda; parado ou patinando a embreagem, vai para o alvo do motor.
        lenta = self._marcha_lenta()
        if self.marcha == 0:
            alvo = lenta + 2500.0 * pedal
        else:
            roda = self._rpm_da_roda(self.marcha)
            patina = lenta + 900.0 * pedal if self.marcha == 1 and self.v * 3.6 < 10 else 0.0
            # Na troca, o rpm cai (ou sobe) até o da marcha nova com a constante de tempo abaixo.
            alvo = max(roda, patina, lenta * 0.9)
        k = 1.0 - math.exp(-dt / 0.15)        # o motor não muda de rotação instantaneamente
        self.rpm = min(RPM_MAX, self.rpm + (alvo - self.rpm) * k)

        # Temperaturas: aquece com a potência, a válvula segura em ~90 °C, perde para o ar.
        potencia = self.rpm / 1000.0 * (0.25 + 0.75 * pedal)
        aquece = 0.075 * potencia + 0.05
        if self.temp_motor > TEMP_TERMOSTATO:
            aquece -= 0.8 * (self.temp_motor - TEMP_TERMOSTATO)
        self.temp_motor += (aquece - 0.0008 * (self.temp_motor - self.temp_ambiente)) * dt
        alvo_ar = self.temp_ambiente + (12.0 if self.v < 3 else 4.0 - 0.02 * self.v * 3.6)
        self.temp_ar += (alvo_ar - self.temp_ar) * (1.0 - math.exp(-dt / 30.0))

        self.combustivel_nivel -= self.consumo_lh() * dt / 3600.0 / 50.0 * 100.0  # tanque de 50 L

    # --- leitura --------------------------------------------------------------------

    def carga(self) -> float:
        pedal = 0.0 if self._troca > 0 else self.acelerador
        return 18.0 + 80.0 * pedal

    def consumo_lh(self) -> float:
        return 0.7 + self.rpm / 1000.0 * self.carga() / 100.0 * 3.2

    def valores(self) -> dict[str, float]:
        ruido = self.rng.gauss
        brutos = {
            "rpm": self.rpm + ruido(0, 8),
            "velocidade": self.v * 3.6,
            "marcha": float(self.marcha),
            "temp_motor": self.temp_motor,
            "temp_ar": self.temp_ar,
            "acelerador": self.acelerador * 100.0,
            "carga": self.carga(),
            "pressao_coletor": 28.0 + 72.0 * self.carga() / 100.0,
            "tensao": 14.1 + ruido(0, 0.03),
            "combustivel_lh": self.consumo_lh(),
            "combustivel_nivel": self.combustivel_nivel,
        }
        return {n: CANAIS[n].limitar(v) for n, v in brutos.items()}


def simular(segundos: float, hz: float = HZ, semente: int = 1,
            temp_inicial: float = 25.0) -> list[tuple[float, dict[str, float]]]:
    """Simulação sem thread nem relógio (determinística): para testes e gráficos."""
    carro = Carro(semente, temp_inicial)
    dt = 1.0 / hz
    saida = []
    for i in range(int(segundos * hz)):
        carro.passo(dt)
        saida.append(((i + 1) * dt, carro.valores()))
    return saida


class FonteSimulada(FontePeriodica):
    def __init__(self, hz: float = HZ, semente: int = 1, temp_inicial: float = 25.0) -> None:
        super().__init__(hz)
        self.semente, self.temp_inicial = semente, temp_inicial
        self._t_anterior = 0.0
        self.carro = Carro(semente, temp_inicial)

    def iniciar(self) -> None:
        self.carro = Carro(self.semente, self.temp_inicial)
        self._t_anterior = 0.0
        super().iniciar()

    def amostrar(self, t: float) -> Mapping[str, float]:
        self.carro.passo(t - self._t_anterior)  # dt real: se a máquina atrasar, o carro não
        self._t_anterior = t                    # anda mais devagar que o relógio
        return self.carro.valores()


def _gravar(segundos: float, caminho: str, semente: int) -> None:
    from core.metricas import cpu_processo_s

    fonte = FonteSimulada(semente=semente)
    linhas: list[str] = []
    ultima = None
    c0, t0 = cpu_processo_s(), time.monotonic()
    fonte.iniciar()
    while time.monotonic() - t0 < segundos:
        time.sleep(0.01)
        u = fonte.ultima()
        if u is not None and u is not ultima:
            ultima = u
            linhas.append(",".join([f"{u.t:.3f}"] + [f"{u.valores[n]:.3f}" for n in CANAIS]))
    fonte.parar()
    duracao = time.monotonic() - t0
    with open(caminho, "w", encoding="utf-8") as arq:
        arq.write(",".join(["t", *CANAIS]) + "\n" + "\n".join(linhas) + "\n")
    print(f"{fonte.leituras} leituras em {duracao:.1f} s = {fonte.leituras / duracao:.2f} Hz; "
          f"{len(linhas)} gravadas; CPU do processo {100 * (cpu_processo_s() - c0) / duracao:.1f}%"
          f"{'; ERRO: ' + repr(fonte.erro) if fonte.erro else ''}")


def main() -> None:
    p = argparse.ArgumentParser(description="Grava a FonteSimulada em CSV (tempo real).")
    p.add_argument("--segundos", type=float, default=60.0)
    p.add_argument("--csv", default="/tmp/simulada.csv")
    p.add_argument("--semente", type=int, default=1)
    a = p.parse_args()
    _gravar(a.segundos, a.csv, a.semente)


if __name__ == "__main__":
    main()
