"""Janela base do Dashamp: 800×480 sem bordas, laço limitado a 30 fps, saída com Esc ou Q.

Todo app do projeto usa `App` e ganha as opções comuns:
  --metricas      imprime fps, CPU e RSS a cada 5 s
  --captura N     salva /tmp/captura.png após N segundos
  --duracao N     encerra sozinho após N segundos (testes e medições pelo SSH)
  --janela        janela com bordas e cursor (desenvolvimento no PC)

Quando aberto pelo deploy/run.sh (variável DASHAMP_ARQUIVO_APP), as teclas F1, F2 e F3 trocam
de app: gravam a escolha no ~/dashamp/.app e encerram; o laço do .xinitrc abre o app novo.

`python -m core.app` abre uma tela de teste (barras de cor, moldura, quadrado animado e fps).
"""
from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable, Sequence

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# Sem isto o SDL usa OpenGL para apresentar a janela e carrega o Mesa + libLLVM: no Eee PC o RSS
# sobe de ~49 MB para ~122 MB. A cópia por software (XShm) basta para 800×480 (ver docs/estado.md).
os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "0")
import pygame  # noqa: E402

from core.captura import Captura
from core.metricas import Metricas

LARGURA, ALTURA = 800, 480
FPS_ALVO = 30

# Tecla → linha do .app (ver deploy/run.sh).
ATALHOS_APP = {pygame.K_F1: "player", pygame.K_F2: "painel --gt7", pygame.K_F3: "painel"}


def arquivo_app() -> str | None:
    return os.environ.get("DASHAMP_ARQUIVO_APP") or None


def gravar_app(linha: str) -> bool:
    """Grava a linha do .app (só quando o app foi aberto pelo run.sh)."""
    caminho = arquivo_app()
    if caminho is None:
        return False
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(linha.strip() + "\n")
    return True


def linha_atalho(tecla: int) -> str:
    """Linha do .app para a tecla; o painel mantém o tema que estava escolhido."""
    linha = ATALHOS_APP[tecla]
    caminho = arquivo_app()
    if linha.startswith("painel") and caminho and os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as f:
            atual = f.readline().split()
        if "--tema" in atual and atual.index("--tema") + 1 < len(atual):
            linha += " --tema " + atual[atual.index("--tema") + 1]
    return linha


def lembrar_opcao(opcao: str, valor: str) -> None:
    """Troca (ou acrescenta) `opcao valor` na linha atual do .app, para valer no próximo boot."""
    caminho = arquivo_app()
    if caminho is None or not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        partes = f.readline().split()
    if opcao in partes:
        i = partes.index(opcao)
        partes[i + 1:i + 2] = [valor]
    else:
        partes += [opcao, valor]
    gravar_app(" ".join(partes))

# Desenha o quadro na tela. Devolve os retângulos alterados (atualização parcial)
# ou None para atualizar a tela inteira.
FuncaoQuadro = Callable[[pygame.Surface, float], Sequence[pygame.Rect] | None]
FuncaoEvento = Callable[[pygame.event.Event], None]


def opcoes_comuns(descricao: str = "Dashamp") -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=descricao)
    p.add_argument("--metricas", action="store_true", help="imprime fps, CPU e RSS a cada 5 s")
    p.add_argument("--captura", type=float, metavar="S", help="salva /tmp/captura.png após S segundos")
    p.add_argument("--duracao", type=float, metavar="S", help="encerra após S segundos")
    p.add_argument("--janela", action="store_true", help="janela com bordas e cursor (PC)")
    return p


class App:
    def __init__(self, args: argparse.Namespace, titulo: str = "Dashamp") -> None:
        # Só vídeo e fonte: pygame.init() abriria o mixer e prenderia o ALSA, que é do GStreamer.
        pygame.display.init()
        pygame.font.init()
        flags = 0 if args.janela else pygame.NOFRAME
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), flags)
        pygame.display.set_caption(titulo)
        pygame.mouse.set_visible(bool(args.janela))
        self.relogio = pygame.time.Clock()
        self.metricas = Metricas() if args.metricas else None
        self.captura = Captura(args.captura) if args.captura is not None else None
        self._fim = time.monotonic() + args.duracao if args.duracao else None
        self.rodando = True

    def _tratar_eventos(self, ao_evento: FuncaoEvento | None) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.rodando = False
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q):
                self.rodando = False
            elif ev.type == pygame.KEYDOWN and ev.key in ATALHOS_APP and arquivo_app():
                gravar_app(linha_atalho(ev.key))
                self.rodando = False
            elif ao_evento is not None:
                ao_evento(ev)

    def _esperar_quadro(self) -> None:
        """Dorme até o próximo horário absoluto de quadro (múltiplos de 1/30 s).

        O Clock.tick(30) dorme 33 ms a partir de agora; com um núcleo dividido com o GStreamer o
        processo acorda ~1 ms atrasado e o atraso se soma (29,4 fps medidos no Eee PC). Com prazos
        absolutos, o atraso de um quadro é descontado no seguinte e a média fica em 30."""
        self._proximo += 1.0 / FPS_ALVO
        espera = self._proximo - time.perf_counter()
        if espera > 0:
            time.sleep(espera)
        elif espera < -1.0 / FPS_ALVO:
            self._proximo = time.perf_counter()  # atrasou mais de um quadro: não corre para compensar

    def rodar(self, quadro: FuncaoQuadro, ao_evento: FuncaoEvento | None = None) -> None:
        primeiro = True
        self._proximo = time.perf_counter()
        while self.rodando:
            self._esperar_quadro()
            dt = self.relogio.tick() / 1000.0  # só mede (fps e dt); quem dorme é _esperar_quadro
            self._tratar_eventos(ao_evento)
            sujos = quadro(self.tela, dt)
            if sujos is None or primeiro:
                pygame.display.flip()
                primeiro = False
            elif sujos:
                pygame.display.update(sujos)
            if self.metricas is not None:
                self.metricas.quadro()
            if self.captura is not None:
                self.captura.verificar(self.tela)
            if self._fim is not None and time.monotonic() >= self._fim:
                self.rodando = False
        pygame.quit()


# ---------------------------------------------------------------------------
# Tela de teste


def _fundo_teste() -> pygame.Surface:
    """Pré-renderiza tudo o que é estático: barras de cor, grade, moldura e título."""
    fundo = pygame.Surface((LARGURA, ALTURA))
    fundo.fill((16, 16, 24))
    cores = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
             (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0)]
    largura_barra = LARGURA // len(cores)
    for i, cor in enumerate(cores):
        fundo.fill(cor, (i * largura_barra, 0, largura_barra, 120))
    for x in range(0, LARGURA, 50):
        pygame.draw.line(fundo, (40, 40, 56), (x, 120), (x, ALTURA))
    for y in range(120, ALTURA, 50):
        pygame.draw.line(fundo, (40, 40, 56), (0, y), (LARGURA, y))
    # Moldura de 1 px nas bordas: confirma que os 800×480 aparecem inteiros.
    pygame.draw.rect(fundo, (255, 64, 64), fundo.get_rect(), 1)
    fonte = pygame.font.Font(None, 40)
    titulo = fonte.render("Dashamp - nucleo F0.7", True, (230, 230, 230))
    fundo.blit(titulo, (20, 140))
    pequena = pygame.font.Font(None, 24)
    dica = pequena.render("800x480 - Esc ou Q para sair", True, (150, 150, 170))
    fundo.blit(dica, (20, 180))
    return fundo


def tela_de_teste(app: App) -> FuncaoQuadro:
    fundo = _fundo_teste()
    fonte = pygame.font.Font(None, 32)
    lado = 40
    quadrado = pygame.Rect(0, 300, lado, lado)
    area_fps = pygame.Rect(LARGURA - 170, 140, 150, 30)
    estado = {"x": 20.0, "vx": 160.0, "fps_txt": None, "antes": quadrado.copy()}

    def quadro(tela: pygame.Surface, dt: float) -> list[pygame.Rect]:
        # Apaga o quadrado antigo restaurando só aquele pedaço do fundo.
        antes: pygame.Rect = estado["antes"]
        tela.blit(fundo, antes, antes)
        estado["x"] += estado["vx"] * dt
        if estado["x"] < 20 or estado["x"] > LARGURA - 20 - lado:
            estado["vx"] = -estado["vx"]
            estado["x"] = min(max(estado["x"], 20), LARGURA - 20 - lado)
        quadrado.x = int(estado["x"])
        tela.fill((255, 200, 0), quadrado)
        sujos = [antes.copy(), quadrado.copy()]
        estado["antes"] = quadrado.copy()
        # O texto do fps só é refeito quando o valor exibido muda.
        fps_txt = f"{app.relogio.get_fps():4.1f} fps"
        if fps_txt != estado["fps_txt"]:
            estado["fps_txt"] = fps_txt
            tela.blit(fundo, area_fps, area_fps)
            tela.blit(fonte.render(fps_txt, True, (120, 255, 120)), area_fps)
            sujos.append(area_fps)
        return sujos

    app.tela.blit(fundo, (0, 0))  # o primeiro quadro sempre faz flip da tela inteira
    return quadro


def main(argv: Sequence[str] | None = None) -> None:
    args = opcoes_comuns("Dashamp - tela de teste do núcleo").parse_args(argv)
    app = App(args, "Dashamp")
    app.rodar(tela_de_teste(app))


if __name__ == "__main__":
    main()
