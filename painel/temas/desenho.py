"""Ferramentas comuns dos geradores de tema (F2.6). Tudo é desenhado por código.

Os geradores desenham o fundo em 2× (`Tela2x`) e reduzem com smoothscale no fim: antisserrilhado
sem custo no Eee PC, porque os PNGs são gerados uma vez (no PC) e commitados.

Fontes: só DejaVu (licença livre), procurada na pasta do sistema (Debian:
fonts-dejavu-core) ou em `tmp/fontes/` (fora do Git; copie de um Linux com
`scp 'eeepc:/usr/share/fonts/truetype/dejavu/*.ttf' tmp/fontes/`). A fonte em si nunca vai para o
repositório, só os PNGs com os números já desenhados.
"""
from __future__ import annotations

import json
import math
import os
import random
from collections.abc import Sequence

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTAS_FONTES = ("/usr/share/fonts/truetype/dejavu", os.path.join(RAIZ, "tmp", "fontes"))
LARGURA, ALTURA = 800, 480
E = 2                                   # fator de supersample do fundo

Cor = tuple[int, int, int]


def iniciar() -> None:
    pygame.display.init()
    pygame.font.init()


def fonte(arquivo: str, tamanho: float) -> pygame.font.Font:
    for pasta in PASTAS_FONTES:
        caminho = os.path.join(pasta, arquivo)
        if os.path.isfile(caminho):
            return pygame.font.Font(caminho, int(round(tamanho)))
    raise SystemExit(f"fonte {arquivo} não encontrada em {', '.join(PASTAS_FONTES)} "
                     "(veja o docstring de painel/temas/desenho.py)")


def angulo(v: float, lo: float, hi: float, zero: float = 225.0, varredura: float = 270.0) -> float:
    """Mesmo mapeamento do widget Ponteiro/Arco: graus anti-horários a partir das 3 h."""
    f = min(1.0, max(0.0, (v - lo) / (hi - lo)))
    return zero - varredura * f


def ponto(c: Sequence[float], graus: float, r: float) -> tuple[float, float]:
    a = math.radians(graus)
    return c[0] + r * math.cos(a), c[1] - r * math.sin(a)


def misturar(a: Cor, b: Cor, t: float) -> Cor:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


class Tela2x:
    """Superfície em 2×; as funções recebem coordenadas de 1× e multiplicam por E."""

    def __init__(self, cor: Cor = (0, 0, 0)) -> None:
        self.s = pygame.Surface((LARGURA * E, ALTURA * E))
        self.s.fill(cor)

    @staticmethod
    def p(xy: Sequence[float]) -> tuple[float, float]:
        return xy[0] * E, xy[1] * E

    def gradiente_vertical(self, topo: Cor, base: Cor) -> None:
        h = self.s.get_height()
        for y in range(h):
            self.s.fill(misturar(topo, base, y / (h - 1)), (0, y, self.s.get_width(), 1))

    def gradiente_radial(self, c: Sequence[float], r: float, centro: Cor, borda: Cor,
                         passos: int = 60) -> None:
        for i in range(passos, 0, -1):
            t = i / passos
            pygame.draw.circle(self.s, misturar(centro, borda, t ** 1.6), self.p(c), r * E * t)

    def circulo(self, c: Sequence[float], r: float, cor: Cor, largura: float = 0) -> None:
        pygame.draw.circle(self.s, cor, self.p(c), r * E, int(largura * E))

    def linha(self, a: Sequence[float], b: Sequence[float], cor: Cor, largura: float) -> None:
        pygame.draw.line(self.s, cor, self.p(a), self.p(b), max(1, int(round(largura * E))))

    def poligono(self, pts: Sequence[Sequence[float]], cor: Cor) -> None:
        pygame.draw.polygon(self.s, cor, [self.p(q) for q in pts])

    def retangulo(self, ret: Sequence[float], cor: Cor, largura: float = 0, raio: float = 0) -> None:
        r = pygame.Rect(ret[0] * E, ret[1] * E, ret[2] * E, ret[3] * E)
        pygame.draw.rect(self.s, cor, r, int(largura * E), border_radius=int(raio * E))

    def texto(self, f: pygame.font.Font, s: str, cor: Cor, c: Sequence[float],
              ancora: str = "center") -> None:
        img = f.render(s, True, cor)
        self.s.blit(img, img.get_rect(**{ancora: self.p(c)}))

    def faixa_arco(self, c: Sequence[float], r_ext: float, r_int: float, a0: float, a1: float,
                   cor: Cor) -> None:
        passos = max(2, int(abs(a1 - a0) / 1.5))
        angs = [a0 + (a1 - a0) * i / passos for i in range(passos + 1)]
        self.poligono([ponto(c, a, r_ext) for a in angs] + [ponto(c, a, r_int) for a in reversed(angs)],
                      cor)

    def bisel(self, c: Sequence[float], r: float, largura: float, claro: Cor, escuro: Cor) -> None:
        """Aro metálico: gradiente do claro (em cima à esquerda) ao escuro, em anel."""
        for i in range(48):
            a0 = 135 + i * 7.5
            t = abs(((i * 7.5) % 360) - 180) / 180            # 0 em 135°, 1 em 315°
            self.faixa_arco(c, r, r - largura, a0, a0 + 7.6, misturar(escuro, claro, t))

    def granulado(self, intensidade: int, semente: int, densidade: float = 0.04) -> None:
        """Textura discreta (couro/plástico): pontos aleatórios um pouco mais claros/escuros."""
        rng = random.Random(semente)
        w, h = self.s.get_size()
        for _ in range(int(w * h * densidade)):
            x, y = rng.randrange(w), rng.randrange(h)
            r, g, b, _a = self.s.get_at((x, y))
            d = rng.randint(-intensidade, intensidade)
            self.s.set_at((x, y), (max(0, min(255, r + d)), max(0, min(255, g + d)),
                                   max(0, min(255, b + d))))

    def reduzir(self) -> pygame.Surface:
        return pygame.transform.smoothscale(self.s, (LARGURA, ALTURA))


def escala(t: Tela2x, c: Sequence[float], r: float, lo: float, hi: float, *, passo_maior: float,
           menores: int, divisor: float, f: pygame.font.Font, cor: Cor, zero: float = 225.0,
           varredura: float = 270.0, r_numeros: float = 0.66, comp_maior: float = 0.14,
           comp_menor: float = 0.07, larg_maior: float = 3.0, larg_menor: float = 1.4,
           formato: str = "{:g}") -> None:
    """Traços e números de um mostrador analógico (o mesmo ângulo do widget Ponteiro)."""
    n = int(round((hi - lo) / passo_maior)) * (menores + 1)
    for i in range(n + 1):
        v = lo + i * passo_maior / (menores + 1)
        a = angulo(v, lo, hi, zero, varredura)
        maior = i % (menores + 1) == 0
        comp = comp_maior if maior else comp_menor
        t.linha(ponto(c, a, r * (1 - comp)), ponto(c, a, r), cor, larg_maior if maior else larg_menor)
        if maior and f is not None:
            t.texto(f, formato.format(v / divisor), cor, ponto(c, a, r * r_numeros))


def zona(t: Tela2x, c: Sequence[float], r_ext: float, r_int: float, lo: float, hi: float,
         de: float, ate: float, cor: Cor, zero: float = 225.0, varredura: float = 270.0) -> None:
    t.faixa_arco(c, r_ext, r_int, angulo(de, lo, hi, zero, varredura),
                 angulo(ate, lo, hi, zero, varredura), cor)


def agulha(comprimento: int, largura: int, cor: Cor, cauda: float = 0.22,
           contrapeso: bool = True) -> pygame.Surface:
    """Sprite do ponteiro: pivô no centro, apontando para a direita (0°), em 4× e reduzido."""
    s4 = 4
    larg_total = 2 * comprimento + 8
    alt = max(largura * 3, 12)
    g = pygame.Surface((larg_total * s4, alt * s4), pygame.SRCALPHA)
    cx, cy = larg_total * s4 / 2, alt * s4 / 2
    base = largura * s4 / 2
    pygame.draw.polygon(g, cor, [(cx - comprimento * cauda * s4, cy - base * 0.8),
                                 (cx + comprimento * s4, cy - 0.6 * s4),
                                 (cx + comprimento * s4, cy + 0.6 * s4),
                                 (cx - comprimento * cauda * s4, cy + base * 0.8)])
    if contrapeso:
        pygame.draw.circle(g, cor, (cx - comprimento * cauda * s4, cy), base * 1.3)
    escuro = misturar(cor, (0, 0, 0), 0.35)
    pygame.draw.line(g, escuro, (cx, cy), (cx + comprimento * 0.9 * s4, cy), max(1, s4 // 2))
    return pygame.transform.smoothscale(g, (larg_total, alt))


def salvar(nome: str, tema: dict, imagens: dict[str, pygame.Surface]) -> str:
    pasta = os.path.join(RAIZ, "painel", "temas", nome)
    os.makedirs(pasta, exist_ok=True)
    for arquivo, img in imagens.items():
        pygame.image.save(img, os.path.join(pasta, arquivo))
    with open(os.path.join(pasta, "tema.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(_json(tema) + "\n")
    print(f"tema {nome}: {', '.join(['tema.json', *imagens])} em {pasta}")
    return pasta


def _json(tema: dict) -> str:
    """JSON legível: um widget/texto por linha."""
    linhas = ["{"]
    itens = list(tema.items())
    for i, (k, v) in enumerate(itens):
        fim = "," if i < len(itens) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            linhas.append(f'  "{k}": [')
            for j, item in enumerate(v):
                linhas.append("    " + json.dumps(item, ensure_ascii=False)
                              + ("," if j < len(v) - 1 else ""))
            linhas.append("  ]" + fim)
        else:
            linhas.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}{fim}')
    linhas.append("}")
    return "\n".join(linhas)


def hexa(c: Cor) -> str:
    return "#%02x%02x%02x" % c
