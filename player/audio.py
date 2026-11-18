"""Motor de áudio: `playbin` do GStreamer numa thread com GLib MainLoop.

- Controles: abrir, tocar, pausar, parar, buscar, volume (0..100), balanço (-100..100).
- Leituras: posição, duração, estado, tags (título, artista, kbps, kHz, canais).
- Espectro: o filtro de áudio é `audiopanorama ! spectrum`; cada mensagem (~20 por segundo) vira
  19 barras 0..1, guardadas num deque curto lido pelo laço do pygame com `espectro()`.
- Eventos (fim da faixa, erro, aviso) vão para a fila `eventos`, também lida pelo laço do pygame.

Teste avulso (sem janela), imprimindo CPU e barras a cada 5 s:
    python -m player.audio ~/musica/teste_320kbps.mp3 --duracao 300
"""
from __future__ import annotations

import argparse
import os
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstAudio", "1.0")
from gi.repository import GLib, Gst, GstAudio  # noqa: E402

from player.espectro import BARRAS, Agrupador  # noqa: E402
from player.tipos_audio import Evento, Tags  # noqa: E402,F401  (reexportados)

N_BANDAS = 512             # 43 Hz por banda a 44,1 kHz: resolução para as barras graves
INTERVALO_ESPECTRO_MS = 50  # ~20 atualizações por segundo
_RE_MAGNITUDE = re.compile(r"magnitude=\(float\)\{([^}]*)\}")


@dataclass
class _Contadores:
    espectros: int = 0
    avisos: list[str] = field(default_factory=list)


class MotorAudio:
    def __init__(self, saida: str = "autoaudiosink") -> None:
        Gst.init(None)
        self.playbin = Gst.ElementFactory.make("playbin", "player")
        # Só áudio (2) e volume por software (16): sem vídeo nem legendas.
        self.playbin.set_property("flags", 0x02 | 0x10)
        # `saida` é uma descrição gst-launch: "autoaudiosink", "alsasink", "fakesink sync=true"...
        self.playbin.set_property("audio-sink", Gst.parse_bin_from_description(saida, True))
        self.playbin.set_property("audio-filter", self._montar_filtro())

        self.tags = Tags()
        self.eventos: queue.Queue[Evento] = queue.Queue()
        self.contadores = _Contadores()
        self._espectros: deque[list[float]] = deque(maxlen=4)
        self._agrupador: Agrupador | None = None
        self._volume = 75
        self.volume(self._volume)

        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._mensagem)
        self._laco = GLib.MainLoop()
        self._thread = threading.Thread(target=self._laco.run, name="gst", daemon=True)
        self._thread.start()

    def _montar_filtro(self) -> Gst.Bin:
        filtro = Gst.Bin.new("filtro")
        conv = Gst.ElementFactory.make("audioconvert", "conv")
        self.panorama = Gst.ElementFactory.make("audiopanorama", "balanco")
        self.spectrum = Gst.ElementFactory.make("spectrum", "espectro")
        self.spectrum.set_property("bands", N_BANDAS)
        self.spectrum.set_property("interval", INTERVALO_ESPECTRO_MS * Gst.MSECOND)
        self.spectrum.set_property("threshold", -80)
        self.spectrum.set_property("post-messages", True)
        self.spectrum.set_property("message-magnitude", True)
        for e in (conv, self.panorama, self.spectrum):
            filtro.add(e)
        conv.link(self.panorama)
        self.panorama.link(self.spectrum)
        filtro.add_pad(Gst.GhostPad.new("sink", conv.get_static_pad("sink")))
        filtro.add_pad(Gst.GhostPad.new("src", self.spectrum.get_static_pad("src")))
        return filtro

    # --- controles ------------------------------------------------------------

    def abrir(self, caminho: str) -> None:
        self.parar()
        self.tags = Tags()
        self._agrupador = None
        self._espectros.clear()
        self.playbin.set_property("uri", Gst.filename_to_uri(os.path.abspath(caminho)))

    def tocar(self) -> None:
        self.playbin.set_state(Gst.State.PLAYING)

    def pausar(self) -> None:
        self.playbin.set_state(Gst.State.PAUSED)

    def parar(self) -> None:
        self.playbin.set_state(Gst.State.READY)
        self._espectros.clear()

    def buscar(self, segundos: float) -> bool:
        return self.playbin.seek_simple(
            Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(max(0.0, segundos) * Gst.SECOND))

    def volume(self, valor: int | None = None) -> int:
        """0..100 numa escala cúbica (como o controle de volume do sistema)."""
        if valor is not None:
            self._volume = max(0, min(100, int(valor)))
            linear = GstAudio.StreamVolume.convert_volume(
                GstAudio.StreamVolumeFormat.CUBIC, GstAudio.StreamVolumeFormat.LINEAR,
                self._volume / 100)
            self.playbin.set_property("volume", linear)
        return self._volume

    def balanco(self, valor: int | None = None) -> int:
        if valor is not None:
            self.panorama.set_property("panorama", max(-100, min(100, int(valor))) / 100)
        return round(self.panorama.get_property("panorama") * 100)

    def fechar(self) -> None:
        self.playbin.set_state(Gst.State.NULL)
        self._laco.quit()

    # --- leituras ---------------------------------------------------------------

    def estado(self) -> str:
        _, atual, _ = self.playbin.get_state(0)
        return {Gst.State.PLAYING: "tocando", Gst.State.PAUSED: "pausado"}.get(atual, "parado")

    def posicao(self) -> float | None:
        ok, ns = self.playbin.query_position(Gst.Format.TIME)
        return ns / Gst.SECOND if ok else None

    def duracao(self) -> float | None:
        ok, ns = self.playbin.query_duration(Gst.Format.TIME)
        return ns / Gst.SECOND if ok and ns > 0 else None

    def espectro(self) -> list[float] | None:
        """Barras mais recentes (0..1), ou None se nada chegou desde a última leitura."""
        try:
            return self._espectros.pop()
        except IndexError:
            return None
        finally:
            self._espectros.clear()

    # --- mensagens (thread do GLib) ---------------------------------------------

    def _mensagem(self, _bus: Gst.Bus, msg: Gst.Message) -> None:
        t = msg.type
        if t == Gst.MessageType.ELEMENT and msg.src is self.spectrum:
            self._ao_espectro(msg.get_structure())
        elif t == Gst.MessageType.TAG:
            self._ao_tags(msg.parse_tag())
        elif t == Gst.MessageType.EOS:
            self.eventos.put(Evento("fim"))
        elif t == Gst.MessageType.ERROR:
            erro, _ = msg.parse_error()
            self.eventos.put(Evento("erro", erro.message))
        elif t == Gst.MessageType.WARNING:
            aviso, _ = msg.parse_warning()
            self.contadores.avisos.append(aviso.message)
            self.eventos.put(Evento("aviso", aviso.message))
        elif t == Gst.MessageType.STREAM_START:
            self._ler_caps()

    def _ao_espectro(self, estrutura: Gst.Structure) -> None:
        # O PyGObject não converte GstValueList; o texto da estrutura é o caminho portátil.
        m = _RE_MAGNITUDE.search(estrutura.to_string())
        if m is None:
            return
        if self._agrupador is None:
            self._ler_caps()
            self._agrupador = Agrupador(N_BANDAS, self.tags.khz * 1000 or 44100, BARRAS)
        self._espectros.append(self._agrupador([float(v) for v in m.group(1).split(",")]))
        self.contadores.espectros += 1

    def _ao_tags(self, lista: Gst.TagList) -> None:
        for nome, attr in (("title", "titulo"), ("artist", "artista")):
            ok, valor = lista.get_string(nome)
            if ok:
                setattr(self.tags, attr, valor)
        for nome in ("bitrate", "nominal-bitrate"):
            ok, valor = lista.get_uint(nome)
            if ok and valor:
                self.tags.kbps = round(valor / 1000)
                break

    def _ler_caps(self) -> None:
        pad = self.playbin.emit("get-audio-pad", 0)
        caps = pad.get_current_caps() if pad is not None else None
        if caps is None or caps.get_size() == 0:
            return
        s = caps.get_structure(0)
        ok, taxa = s.get_int("rate")
        if ok:
            self.tags.khz = round(taxa / 1000)
        ok, canais = s.get_int("channels")
        if ok:
            self.tags.canais = canais


# ---------------------------------------------------------------------------
# Teste avulso


def _barras_texto(barras: list[float]) -> str:
    niveis = " .:-=+*#%@"
    return "".join(niveis[min(9, int(b * 9.99))] for b in barras)


def main() -> None:
    from core.metricas import CpuSistema, cpu_processo_s, rss_mb

    p = argparse.ArgumentParser(description="Dashamp - motor de áudio (teste sem janela)")
    p.add_argument("arquivo")
    p.add_argument("--duracao", type=float, default=30.0, help="segundos tocando")
    p.add_argument("--saida", default="autoaudiosink", help="elemento de saída (ex.: fakesink)")
    args = p.parse_args()

    motor = MotorAudio(args.saida)
    motor.abrir(args.arquivo)
    motor.tocar()
    cpu_sis = CpuSistema()
    t0 = time.monotonic()
    cpu0 = cpu_processo_s()
    pos0: float | None = None
    amostras_sis: list[float] = []
    ultimo = t0
    fim = False
    while time.monotonic() - t0 < args.duracao and not fim:
        time.sleep(0.05)  # simula o laço do pygame lendo o espectro a 20 Hz
        barras = motor.espectro()
        while not motor.eventos.empty():
            ev = motor.eventos.get()
            print(f"[evento] {ev.tipo} {ev.texto}", flush=True)
            fim = fim or ev.tipo in ("fim", "erro")
        agora = time.monotonic()
        if pos0 is None and motor.posicao():
            pos0, t_pos0 = motor.posicao(), agora
        if agora - ultimo >= 5:
            sis = cpu_sis.percentual()
            if sis is not None:
                amostras_sis.append(sis)
            cpu = 100 * (cpu_processo_s() - cpu0) / (agora - t0)
            pos = motor.posicao() or 0.0
            print(f"{pos:6.1f}/{motor.duracao() or 0:5.1f}s | proc {cpu:4.1f}% | sistema "
                  f"{sis or 0:4.1f}% | rss {rss_mb() or 0:5.1f} MB | espectros "
                  f"{motor.contadores.espectros / (agora - t0):4.1f}/s | "
                  f"[{_barras_texto(barras) if barras else ' ' * BARRAS}]", flush=True)
            ultimo = agora
    total = time.monotonic() - t0
    pos_final = motor.posicao() or 0.0
    deriva = (pos_final - pos0) - (time.monotonic() - t_pos0) if pos0 is not None else float("nan")
    print(f"tags: {motor.tags}")
    print(f"resumo: {total:.0f} s | CPU do sistema média {sum(amostras_sis) / max(1, len(amostras_sis)):.1f}% "
          f"(máx {max(amostras_sis, default=0):.1f}%) | avisos {len(motor.contadores.avisos)} | "
          f"deriva posição×relógio {deriva:+.2f} s | espectros {motor.contadores.espectros}")
    motor.fechar()


if __name__ == "__main__":
    main()
