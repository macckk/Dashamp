"""Gera um MP3 sintético para testar o áudio (F1.5): sem direitos autorais, pode ser recriado.

    python3 scripts/gerar_mp3_teste.py [saida.mp3] [--segundos 300] [--kbps 320]

Conteúdo: varredura logarítmica de 40 Hz a 16 kHz a cada 8 s (subindo no canal esquerdo, descendo
no direito) e uma batida grave a cada 0,5 s; assim todas as barras do analisador se mexem.
O WAV intermediário fica no /tmp (tmpfs) e é apagado no fim. Usa numpy e GStreamer (lamemp3enc).
"""
from __future__ import annotations

import argparse
import os
import wave

import numpy as np

TAXA = 44100
CICLO_S = 8.0
F0, F1 = 40.0, 16000.0
TRECHO_S = 10  # gerado em pedaços para não ocupar memória


def trecho(inicio_s: float, dur_s: float) -> np.ndarray:
    t = inicio_s + np.arange(int(dur_s * TAXA)) / TAXA
    fase_ciclo = (t % CICLO_S) / CICLO_S
    k = np.log(F1 / F0)
    # Fase da varredura exponencial: integral de F0·e^(k·u) em relação ao tempo dentro do ciclo.
    fase_sobe = 2 * np.pi * F0 * CICLO_S / k * (np.exp(k * fase_ciclo) - 1)
    fase_desce = 2 * np.pi * F1 * CICLO_S / k * (1 - np.exp(-k * fase_ciclo))
    batida_t = t % 0.5
    batida = np.sin(2 * np.pi * 55 * batida_t) * np.exp(-batida_t * 18)
    esquerdo = 0.30 * np.sin(fase_sobe) + 0.35 * batida
    direito = 0.30 * np.sin(fase_desce) + 0.35 * batida
    estereo = np.empty((t.size, 2), dtype=np.int16)
    estereo[:, 0] = np.clip(esquerdo * 32767, -32768, 32767)
    estereo[:, 1] = np.clip(direito * 32767, -32768, 32767)
    return estereo


def gerar_wav(caminho: str, segundos: int) -> None:
    with wave.open(caminho, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        for inicio in range(0, segundos, TRECHO_S):
            w.writeframes(trecho(inicio, min(TRECHO_S, segundos - inicio)).tobytes())


def codificar_mp3(wav: str, mp3: str, kbps: int, titulo: str = "Varredura de teste") -> None:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    pipeline = Gst.parse_launch(
        f'filesrc location="{wav}" ! wavparse ! audioconvert ! '
        f"lamemp3enc target=bitrate bitrate={kbps} cbr=true ! "
        f'id3v2mux name=mux ! filesink location="{mp3}"'
    )
    # As tags vão direto no id3v2mux (GstTagSetter); o taginject não aceita valores com espaço.
    tags = Gst.TagList.new_from_string(
        f'taglist, title="{titulo}", artist="Dashamp", album="Sinais sinteticos"')
    pipeline.get_by_name("mux").merge_tags(tags, Gst.TagMergeMode.REPLACE_ALL)
    pipeline.set_state(Gst.State.PLAYING)
    msg = pipeline.get_bus().timed_pop_filtered(
        Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    pipeline.set_state(Gst.State.NULL)
    if msg.type == Gst.MessageType.ERROR:
        raise SystemExit(f"erro ao codificar: {msg.parse_error()[0].message}")


def gerar_lista(pasta: str, n: int) -> None:
    """Faixas 'Faixa 01'..'Faixa N' para testar a playlist (F1.7); repetir pula as que já existem."""
    os.makedirs(pasta, exist_ok=True)
    wav = "/tmp/dashamp_lista.wav" if os.path.isdir("/tmp") else os.path.join(pasta, "tmp.wav")
    for i in range(1, n + 1):
        mp3 = os.path.join(pasta, f"faixa_{i:02d}.mp3")
        if os.path.exists(mp3):
            continue
        segundos = 6 + (i * 7) % 15
        kbps = (128, 192, 320)[i % 3]
        try:
            gerar_wav(wav, segundos)
            codificar_mp3(wav, mp3, kbps, titulo=f"Faixa {i:02d}")
        finally:
            if os.path.exists(wav):
                os.remove(wav)
        print(f"{mp3}: {segundos} s, {kbps} kbps", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("saida", nargs="?", default=os.path.expanduser("~/musica/teste_320kbps.mp3"))
    p.add_argument("--segundos", type=int, default=300)
    p.add_argument("--kbps", type=int, default=320)
    p.add_argument("--lista", type=int, metavar="N",
                   help="gera N faixas curtas (6–20 s; 128/192/320 kbps) na pasta `saida`")
    args = p.parse_args()
    if args.lista:
        gerar_lista(args.saida, args.lista)
        return
    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    wav = "/tmp/dashamp_teste.wav" if os.path.isdir("/tmp") else args.saida + ".wav"
    try:
        gerar_wav(wav, args.segundos)
        codificar_mp3(wav, args.saida, args.kbps)
    finally:
        if os.path.exists(wav):
            os.remove(wav)
    print(f"{args.saida}: {args.segundos} s, {args.kbps} kbps, "
          f"{os.path.getsize(args.saida) / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
