"""F0.8 — teste decisivo de desempenho: mostrador 400×400 pré-renderizado + ponteiro girando.

Variações:
  --modo rotacao   pygame.transform.rotate a cada quadro
  --modo cache     360 sprites pré-rotacionados (com antisserrilhado, recortados no mínimo)
  --mostradores 1|2   um mostrador no centro ou dois lado a lado (tela cheia 800×480)
  --atualizacao parcial|total   redesenha só o que muda (padrão) ou a tela inteira a cada quadro

Exemplo: python -m core.bench_ponteiro --modo cache --mostradores 2 --metricas --duracao 30
"""
from __future__ import annotations

import math
import time
from collections.abc import Sequence

from core.app import ALTURA, LARGURA, App, opcoes_comuns

import pygame  # noqa: E402  (core.app ajusta o ambiente do SDL antes)

LADO = 400                 # mostrador 400×400
RAIO = LADO // 2
COMPRIMENTO = 165          # do pivô até a ponta do ponteiro
VARREDURA = 270.0          # graus de 0 a 100%
ANGULO_ZERO = 225.0        # 0% embaixo à esquerda; ângulo matemático (anti-horário)
PERIODO_S = 4.0            # vai e volta do ponteiro

COR_FUNDO = (12, 12, 16)
COR_FACE = (236, 228, 205)
COR_TRACO = (30, 30, 30)
COR_ALERTA = (200, 30, 30)
COR_PONTEIRO = (220, 20, 20)


# ---------------------------------------------------------------------------
# Pré-renderização (feita uma vez; o custo não entra no laço)


def _angulo(fracao: float) -> float:
    return ANGULO_ZERO - VARREDURA * fracao


def _ponto(cx: float, cy: float, graus: float, r: float) -> tuple[float, float]:
    rad = math.radians(graus)
    return cx + r * math.cos(rad), cy - r * math.sin(rad)


def desenhar_face(escala: int = 2) -> pygame.Surface:
    """Desenha em 2× e reduz com smoothscale: antisserrilhado barato, só na carga."""
    s = escala
    lado = LADO * s
    c = lado / 2
    face = pygame.Surface((lado, lado))
    face.fill(COR_FUNDO)
    pygame.draw.circle(face, (90, 90, 90), (c, c), (RAIO - 2) * s)
    pygame.draw.circle(face, COR_FACE, (c, c), (RAIO - 10) * s)
    # Faixa vermelha de 80% a 100%.
    for i in range(80, 101):
        a = _angulo(i / 100)
        pygame.draw.line(face, COR_ALERTA, _ponto(c, c, a, (RAIO - 40) * s),
                         _ponto(c, c, a, (RAIO - 14) * s), 5 * s)
    fonte = pygame.font.Font(None, 34 * s)
    for i in range(0, 41):  # 40 divisões; número a cada 5 (0..8 ×1000 rpm)
        a = _angulo(i / 40)
        maior = i % 5 == 0
        r_int = (RAIO - (42 if maior else 30)) * s
        pygame.draw.line(face, COR_TRACO, _ponto(c, c, a, r_int),
                         _ponto(c, c, a, (RAIO - 14) * s), (4 if maior else 2) * s)
        if maior:
            txt = fonte.render(str(i // 5), True, COR_TRACO)
            face.blit(txt, txt.get_rect(center=_ponto(c, c, a, (RAIO - 66) * s)))
    rotulo = pygame.font.Font(None, 26 * s).render("x1000 rpm", True, (90, 90, 90))
    face.blit(rotulo, rotulo.get_rect(center=(c, c + 70 * s)))
    return pygame.transform.smoothscale(face, (LADO, LADO))


def desenhar_ponteiro() -> pygame.Surface:
    """Sprite com o pivô no centro: largura 2×COMPRIMENTO, ponteiro na metade direita (0°)."""
    larg, alt = 2 * COMPRIMENTO + 8, 18
    sprite = pygame.Surface((larg, alt), pygame.SRCALPHA)
    cx, cy = larg / 2, alt / 2
    pygame.draw.polygon(sprite, COR_PONTEIRO,
                        [(cx - 24, cy - 6), (cx + COMPRIMENTO, cy - 1.5),
                         (cx + COMPRIMENTO, cy + 1.5), (cx - 24, cy + 6)])
    return sprite.convert_alpha()


def desenhar_cubo() -> pygame.Surface:
    cubo = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.circle(cubo, (40, 40, 40), (15, 15), 14)
    pygame.draw.circle(cubo, (110, 110, 110), (15, 15), 6)
    return cubo.convert_alpha()


class CachePonteiro:
    """360 ângulos inteiros, rotacionados com rotozoom (suave) e recortados ao conteúdo."""

    def __init__(self, sprite: pygame.Surface) -> None:
        t0 = time.monotonic()
        self.quadros: list[tuple[pygame.Surface, int, int]] = []
        bytes_total = 0
        for graus in range(360):
            girado = pygame.transform.rotozoom(sprite, graus, 1.0)
            caixa = girado.get_bounding_rect()
            recorte = girado.subsurface(caixa).copy().convert_alpha()
            # Deslocamento do canto do recorte em relação ao pivô (centro do girado).
            dx = caixa.x - girado.get_width() // 2
            dy = caixa.y - girado.get_height() // 2
            self.quadros.append((recorte, dx, dy))
            bytes_total += recorte.get_width() * recorte.get_height() * 4
        self.segundos_carga = time.monotonic() - t0
        self.mb = bytes_total / 2**20

    def obter(self, graus: float) -> tuple[pygame.Surface, int, int]:
        return self.quadros[int(round(graus)) % 360]


# ---------------------------------------------------------------------------
# Quadro


class Mostrador:
    def __init__(self, centro: tuple[int, int], fase: float) -> None:
        self.centro = centro
        self.fase = fase
        self.ret_anterior = pygame.Rect(centro, (0, 0))

    def fracao(self, t: float) -> float:
        return 0.5 + 0.5 * math.sin(2 * math.pi * (t / PERIODO_S + self.fase))


def montar_bench(app: App, modo: str, n_mostradores: int, total: bool):
    face = desenhar_face()
    sprite = desenhar_ponteiro()
    cubo = desenhar_cubo()
    cache = CachePonteiro(sprite) if modo == "cache" else None
    if cache is not None:
        print(f"cache: 360 sprites, {cache.mb:.1f} MB, gerado em {cache.segundos_carga:.2f} s",
              flush=True)

    centros = [(LARGURA // 2, ALTURA // 2)] if n_mostradores == 1 else \
        [(LARGURA // 4, ALTURA // 2), (3 * LARGURA // 4, ALTURA // 2)]
    mostradores = [Mostrador(c, i * 0.37) for i, c in enumerate(centros)]

    fundo = pygame.Surface((LARGURA, ALTURA)).convert()
    fundo.fill(COR_FUNDO)
    for m in mostradores:
        fundo.blit(face, face.get_rect(center=m.centro))
    rotulo = pygame.font.Font(None, 22).render(
        f"{modo} | {n_mostradores} mostrador(es) | {'total' if total else 'parcial'}",
        True, (120, 120, 140))
    fundo.blit(rotulo, (8, ALTURA - 22))
    fonte_fps = pygame.font.Font(None, 30)
    area_fps = pygame.Rect(8, 6, 120, 26)
    estado: dict[str, object] = {"fps": None}
    t0 = time.monotonic()
    app.tela.blit(fundo, (0, 0))

    def ponteiro(graus: float) -> tuple[pygame.Surface, int, int]:
        if cache is not None:
            return cache.obter(graus)
        girado = pygame.transform.rotate(sprite, graus)
        return girado, -(girado.get_width() // 2), -(girado.get_height() // 2)

    def quadro(tela: pygame.Surface, dt: float) -> Sequence[pygame.Rect] | None:
        t = time.monotonic() - t0
        sujos: list[pygame.Rect] = []
        if total:
            tela.blit(fundo, (0, 0))
        for m in mostradores:
            if not total:
                tela.blit(fundo, m.ret_anterior, m.ret_anterior)
            img, dx, dy = ponteiro(_angulo(m.fracao(t)))
            ret = tela.blit(img, (m.centro[0] + dx, m.centro[1] + dy))
            ret_cubo = tela.blit(cubo, cubo.get_rect(center=m.centro))
            novo = ret.union(ret_cubo)
            sujos.append(novo.union(m.ret_anterior))
            m.ret_anterior = novo
        texto = f"{app.relogio.get_fps():4.1f} fps"
        if total or texto != estado["fps"]:
            estado["fps"] = texto
            if not total:
                tela.blit(fundo, area_fps, area_fps)
            tela.blit(fonte_fps.render(texto, True, (120, 255, 120)), area_fps)
            sujos.append(area_fps)
        return None if total else sujos

    return quadro


def main(argv: Sequence[str] | None = None) -> None:
    p = opcoes_comuns("Dashamp - bench do ponteiro (F0.8)")
    p.add_argument("--modo", choices=("rotacao", "cache"), default="rotacao")
    p.add_argument("--mostradores", type=int, choices=(1, 2), default=1)
    p.add_argument("--atualizacao", choices=("parcial", "total"), default="parcial")
    args = p.parse_args(argv)
    app = App(args, "Dashamp bench")
    app.rodar(montar_bench(app, args.modo, args.mostradores, args.atualizacao == "total"))


if __name__ == "__main__":
    main()
