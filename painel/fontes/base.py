"""Interface das fontes de dados do painel (F2.1).

Uma `Fonte` produz `Leitura`s numa thread própria; o laço de quadros só chama `ultima()`, que
devolve a leitura mais recente sem bloquear (troca de referência sob um lock curto). Assim a
fonte pode ter o ritmo que quiser (simulação a 8 Hz, pacotes UDP a 60 Hz, OBD a ~10 Hz) sem
atrasar o desenho a 30 fps.

Duas formas de escrever uma fonte:
- `FontePeriodica`: implemente `amostrar(t) -> dict` e ela é chamada `hz` vezes por segundo
  (simulação, replay);
- `Fonte`: implemente `_rodar()` quando o ritmo vem de fora (socket UDP, porta serial do OBD),
  chamando `self._publicar(valores)` a cada dado novo e saindo quando `self._parar.is_set()`.

Quem precisa de *todas* as leituras (o gravador) usa `assinar(func)`: `func(leitura)` é chamada
na thread da fonte a cada publicação, e por isso deve ser rápida (só enfileirar).

Os valores usam os nomes do catálogo `CANAIS` (unidades fixas: km/h, °C, %, V, L/h...). Cada
leitura traz só os canais que a fonte conhece; o widget de um canal ausente fica parado.
"""
from __future__ import annotations

import abc
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True)
class Canal:
    nome: str
    unidade: str
    minimo: float
    maximo: float
    descricao: str

    def limitar(self, valor: float) -> float:
        return min(self.maximo, max(self.minimo, valor))


def _c(nome: str, unidade: str, minimo: float, maximo: float, descricao: str) -> Canal:
    return Canal(nome, unidade, minimo, maximo, descricao)


# Faixas = o que um carro de passeio pode mostrar; um tema escolhe a escala do mostrador dentro
# delas. Os nomes batem com os PIDs do OBD-II usados na fase 3 (entre parênteses).
CANAIS: Mapping[str, Canal] = MappingProxyType({c.nome: c for c in (
    _c("rpm", "rpm", 0, 9000, "rotação do motor (01 0C)"),
    _c("velocidade", "km/h", 0, 260, "velocidade do veículo (01 0D)"),
    _c("marcha", "", -1, 8, "marcha engatada; 0 = neutro, -1 = ré (OBD: estimada pela razão "
       "rpm/velocidade; F1: até 8)"),
    _c("temp_motor", "°C", -40, 150, "temperatura do líquido de arrefecimento (01 05)"),
    _c("temp_ar", "°C", -40, 100, "temperatura do ar de admissão (01 0F)"),
    _c("acelerador", "%", 0, 100, "posição do acelerador (01 11)"),
    _c("carga", "%", 0, 100, "carga calculada do motor (01 04)"),
    _c("pressao_coletor", "kPa", 0, 255, "pressão absoluta do coletor (01 0B)"),
    _c("tensao", "V", 0, 18, "tensão da bateria / módulo de controle (01 42)"),
    _c("combustivel_lh", "L/h", 0, 40, "consumo instantâneo de combustível"),
    _c("combustivel_nivel", "%", 0, 100, "nível do tanque (01 2F)"),
)})


# Valores publicados quando o jogo deixa de mandar o carro (fim da corrida, pausa, menus): os
# mostradores de movimento voltam ao zero. Temperatura e tanque ficam no último valor: zerá-los
# acenderia as luzes de motor frio e de reserva sem motivo.
REPOUSO: Mapping[str, float] = MappingProxyType(
    {"rpm": 0.0, "velocidade": 0.0, "marcha": 0.0, "acelerador": 0.0})
SILENCIO_REPOUSO_S = 1.5        # sem dado do carro por este tempo: repouso


def canais_desconhecidos(valores: Mapping[str, float]) -> list[str]:
    return [n for n in valores if n not in CANAIS]


@dataclass(frozen=True)
class Leitura:
    """`t`: segundos desde o início da fonte (relógio monotônico, ou o tempo gravado no replay)."""
    t: float
    valores: Mapping[str, float] = field(default_factory=dict)


class Fonte(abc.ABC):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultima: Leitura | None = None
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self.leituras = 0                # quantas leituras já publicou (para métricas e testes)
        self.erro: BaseException | None = None
        self._assinantes: list[Callable[[Leitura], None]] = []

    # --- usado pelo app -----------------------------------------------------------

    def iniciar(self) -> None:
        if self.ativa:
            raise RuntimeError(f"{type(self).__name__} já está rodando")
        self._parar.clear()
        self.erro = None
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._executar, name=type(self).__name__,
                                        daemon=True)
        self._thread.start()

    def parar(self, espera_s: float = 2.0) -> None:
        self._parar.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(espera_s)
        self._thread = None

    def ultima(self) -> Leitura | None:
        with self._lock:
            return self._ultima

    def assinar(self, func: Callable[[Leitura], None]) -> None:
        """`func(leitura)` a cada leitura publicada, chamada na thread da fonte."""
        self._assinantes.append(func)

    def cancelar_assinatura(self, func: Callable[[Leitura], None]) -> None:
        if func in self._assinantes:
            self._assinantes.remove(func)

    @property
    def ativa(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def __enter__(self) -> Fonte:
        self.iniciar()
        return self

    def __exit__(self, *_: object) -> None:
        self.parar()

    # --- usado pelas subclasses -----------------------------------------------------

    @abc.abstractmethod
    def _rodar(self) -> None:
        """Corpo da thread: produz dados até `self._parar` ser sinalizado."""

    def _agora(self) -> float:
        return time.monotonic() - self._t0

    def _publicar(self, valores: Mapping[str, float], t: float | None = None) -> Leitura:
        leitura = Leitura(self._agora() if t is None else t, MappingProxyType(dict(valores)))
        with self._lock:
            self._ultima = leitura
            self.leituras += 1
        for func in tuple(self._assinantes):
            func(leitura)
        return leitura

    def _executar(self) -> None:
        try:
            self._rodar()
        except Exception as e:  # noqa: BLE001 — a thread não pode morrer calada
            self.erro = e


class FontePeriodica(Fonte):
    """Chama `amostrar(t)` `hz` vezes por segundo, em instantes absolutos (sem deriva)."""

    def __init__(self, hz: float) -> None:
        super().__init__()
        if hz <= 0:
            raise ValueError("hz deve ser positivo")
        self.hz = hz

    @abc.abstractmethod
    def amostrar(self, t: float) -> Mapping[str, float]:
        """Valores no instante `t` (s desde o início)."""

    def _rodar(self) -> None:
        periodo = 1.0 / self.hz
        proximo = time.monotonic()
        while not self._parar.is_set():
            t = self._agora()
            self._publicar(self.amostrar(t), t)
            proximo += periodo
            espera = proximo - time.monotonic()
            if espera < -periodo:          # atrasou demais (máquina ocupada): não tenta compensar
                proximo = time.monotonic()
                espera = 0.0
            if espera > 0 and self._parar.wait(espera):
                break
