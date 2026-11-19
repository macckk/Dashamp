"""Tela de teste da F2.4: um widget de cada tipo, alimentado pela FonteSimulada (ou um replay).

    python -m painel.teste_widgets [--replay viagem.db --velocidade 2] [--metricas] [--captura 8]

Esquerda: conta-giros (Ponteiro) com a marcha (Digitos) dentro, para exercitar a sobreposição.
Direita: velocidade (Digitos), temperatura do motor e acelerador (Barra), luzes (LuzEspia) e o
histórico da velocidade (Historico). Esc/Q sai.
"""
from __future__ import annotations

from collections.abc import Sequence

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402

from painel.fontes.base import Fonte  # noqa: E402
from painel.widgets import (  # noqa: E402
    Barra, Digitos, Historico, LuzEspia, Painel, Ponteiro, Zona,
)

VERMELHO, AMBAR, AZUL, VERDE = (230, 40, 30), (255, 170, 0), (60, 140, 255), (40, 220, 60)
CINZA = (150, 150, 160)


def montar_widgets() -> list:
    return [
        Ponteiro("rpm", (220, 240), 200, 0, 8000, passo_maior=1000, divisor=1000,
                 rotulo="x1000 rpm", zonas=[Zona(6000, 8000, VERMELHO)]),
        Digitos("marcha", (204, 318), 1, 56, 0, 6, tau=0, cor=(35, 35, 35),
                cor_apagada=(222, 214, 190)),
        Digitos("velocidade", (480, 28), 3, 96, 0, 260, cor=(255, 80, 30),
                zonas=[Zona(121, 260, AMBAR)]),
        Barra("temp_motor", (460, 168, 320, 26), 20, 130, segmentos=22,
              zonas=[Zona(20, 60, AZUL), Zona(105, 130, VERMELHO)]),
        Barra("acelerador", (460, 230, 320, 16), 0, 100, segmentos=25, tau=0.08,
              cor=VERDE, zonas=[Zona(85, 100, AMBAR)]),
        LuzEspia("rpm", (490, 292), 12, [Zona(5000, 9000, VERMELHO)], rotulo="TROCA",
                 piscar_hz=6),
        LuzEspia("temp_motor", (570, 292), 12, [Zona(-40, 50, AZUL), Zona(105, 150, VERMELHO)],
                 rotulo="TEMP"),
        LuzEspia("tensao", (650, 292), 12, [Zona(0, 12.2, AMBAR)], rotulo="BAT"),
        LuzEspia("velocidade", (730, 292), 12, [Zona(0, 0.5, VERDE)], rotulo="PARADO"),
        Historico("velocidade", (460, 340, 320, 122), 0, 140, segundos=60,
                  zonas=[Zona(110, 140, AMBAR)]),
    ]


def decorar(fundo: pygame.Surface) -> None:
    f = pygame.font.Font(None, 22)
    for texto, pos in (("km/h", (700, 110)), ("temp. motor 20-130 °C", (460, 150)),
                       ("acelerador", (460, 212)), ("velocidade, últimos 60 s", (460, 465))):
        fundo.blit(f.render(texto, True, CINZA), pos)


def criar_fonte(replay: str | None, velocidade: float) -> Fonte:
    if replay:
        from painel.fontes.replay import FonteReplay

        return FonteReplay(replay, velocidade=velocidade, repetir=True)
    from painel.fontes.simulada import FonteSimulada

    return FonteSimulada()


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - teste dos widgets")
    p.add_argument("--replay", help="viagem .db em vez da simulação")
    p.add_argument("--velocidade", type=float, default=1.0)
    args = p.parse_args(argv)
    app = App(args, "Dashamp - widgets")
    painel = Painel((LARGURA, ALTURA), montar_widgets(), decorar=decorar)
    fonte = criar_fonte(args.replay, args.velocidade)

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect] | None:
        painel.atualizar(fonte, dt)
        return painel.desenhar(tela)

    fonte.iniciar()
    try:
        app.rodar(quadro)
    finally:
        fonte.parar()
        if fonte.erro:
            print(f"erro na fonte: {fonte.erro!r}", flush=True)


if __name__ == "__main__":
    main()
