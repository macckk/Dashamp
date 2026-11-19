"""FonteReplay (F2.3): toca uma viagem gravada (formato de `painel.gravacao`) no tempo real.

`velocidade` (1 = tempo real, 4 = quatro vezes mais rápido...) pode mudar durante a reprodução;
`repetir` volta ao começo no fim. As leituras saem com o `t` gravado, e os valores são
acumulados: um canal que não veio numa leitura mantém o último valor (útil para OBD, em que cada
PID tem o seu ritmo).

Verificação no Eee PC (aceite da F2.3): grava N s da FonteSimulada em tempo real, reproduz a
gravação e compara cada leitura com a original:

    python -m painel.fontes.replay --verificar 60 --velocidade 4 --arquivo /tmp/viagem.db
"""
from __future__ import annotations

import argparse
import threading
import time

from painel.fontes.base import Fonte, Leitura
from painel.gravacao import Gravador, ler_metadados, ler_viagem


class FonteReplay(Fonte):
    def __init__(self, caminho: str, velocidade: float = 1.0, repetir: bool = False) -> None:
        super().__init__()
        self.caminho = caminho
        self.metadados = ler_metadados(caminho)   # falha cedo se o arquivo não é uma viagem
        self.repetir = repetir
        self.terminou = threading.Event()
        self._vel_lock = threading.Lock()
        self._velocidade = 1.0
        self._ancora = (0.0, 0.0)                  # (t dos dados, relógio) para o cálculo do tempo
        self.velocidade = velocidade

    @property
    def velocidade(self) -> float:
        return self._velocidade

    @velocidade.setter
    def velocidade(self, valor: float) -> None:
        if valor <= 0:
            raise ValueError("velocidade deve ser positiva")
        with self._vel_lock:
            # Re-ancora: o ponto atual da viagem continua onde está, só o ritmo muda.
            agora = time.monotonic()
            self._ancora = (self._t_dados(agora), agora)
            self._velocidade = valor

    def _t_dados(self, relogio: float) -> float:
        t0, r0 = self._ancora
        return t0 + (relogio - r0) * self._velocidade

    def _rodar(self) -> None:
        self.terminou.clear()
        while not self._parar.is_set():
            self._uma_passada()
            if not self.repetir:
                break
        self.terminou.set()

    def _uma_passada(self) -> None:
        estado: dict[str, float] = {}
        primeiro = True
        for t, valores in ler_viagem(self.caminho):
            if primeiro:
                with self._vel_lock:
                    self._ancora = (t, time.monotonic())
                primeiro = False
            while True:  # espera o instante desta leitura (o ritmo pode mudar no meio)
                with self._vel_lock:
                    falta = (t - self._t_dados(time.monotonic())) / self._velocidade
                if falta <= 0:
                    break
                if self._parar.wait(min(falta, 0.1)):
                    return
            estado.update(valores)
            self._publicar(estado, t)


def _verificar(segundos: float, velocidade: float, arquivo: str) -> bool:
    import os

    from painel.fontes.simulada import FonteSimulada

    if os.path.exists(arquivo):
        os.remove(arquivo)
    originais: list[Leitura] = []
    fonte = FonteSimulada()
    fonte.assinar(originais.append)
    with Gravador(arquivo, {"fonte": "FonteSimulada", "hz": fonte.hz}) as grav:
        grav.acompanhar(fonte)
        with fonte:
            time.sleep(segundos)
    print(f"gravadas {grav.leituras} leituras em {grav.lotes} lotes; "
          f"{os.path.getsize(arquivo) / 1024:.0f} kB", flush=True)

    reproduzidas: list[Leitura] = []
    replay = FonteReplay(arquivo, velocidade=velocidade)
    replay.assinar(reproduzidas.append)
    t0 = time.monotonic()
    with replay:
        replay.terminou.wait(segundos / velocidade + 10)
    duracao = time.monotonic() - t0
    esperado = (originais[-1].t - originais[0].t) / velocidade
    iguais = len(originais) == len(reproduzidas) and all(
        a.t == b.t and dict(a.valores) == dict(b.valores) for a, b in zip(originais, reproduzidas))
    print(f"reproduzidas {len(reproduzidas)} de {len(originais)} em {duracao:.2f} s "
          f"(esperado {esperado:.2f} s a {velocidade:g}×); valores iguais: {iguais}"
          f"{'; ERRO: ' + repr(replay.erro) if replay.erro else ''}")
    print("metadados:", ler_metadados(arquivo))
    return iguais


def main() -> None:
    p = argparse.ArgumentParser(description="Grava a FonteSimulada e confere o replay.")
    p.add_argument("--verificar", type=float, default=60.0, metavar="S")
    p.add_argument("--velocidade", type=float, default=4.0)
    p.add_argument("--arquivo", default="/tmp/viagem.db")
    a = p.parse_args()
    raise SystemExit(0 if _verificar(a.verificar, a.velocidade, a.arquivo) else 1)


if __name__ == "__main__":
    main()
