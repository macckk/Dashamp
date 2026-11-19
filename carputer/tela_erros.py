"""Tela de códigos de erro do OBD-II (F3.2), aberta por cima do painel com a tecla **E**.

Mostra os códigos armazenados (modo 03, os que acendem a luz da injeção) e os pendentes (modo 07,
falhas vistas uma vez que ainda não acenderam a luz), com a descrição do python-OBD (em inglês;
uma tradução de milhares de códigos não cabe aqui) e o sistema em português.

Teclas: **L** lê de novo, **A** apaga (pede confirmação: **S** apaga, **N** cancela), **E** volta
ao painel. Os pedidos vão pela `FonteOBD` (a porta do ELM327 é uma só).

A tela só é redesenhada quando o estado muda.
"""
from __future__ import annotations

import time
from concurrent.futures import Future

import pygame

from painel.fontes.obd import TIPOS_ERRO, Codigo, FonteOBD

LARGURA, ALTURA = 800, 480
ESPERA_MAX_S = 20.0              # sem resposta até aqui: desiste (o ELM pode demorar no modo 04)
MAX_LINHAS = 7

COR_FUNDO = (12, 14, 18)
COR_TITULO = (255, 170, 30)
COR_TEXTO = (235, 235, 235)
COR_FRACO = (140, 146, 156)
COR_ERRO = (255, 80, 60)
COR_OK = (90, 220, 110)

SISTEMAS = {"P": "motor e câmbio", "C": "chassi", "B": "carroceria", "U": "rede de módulos"}


def sistema(codigo: str) -> str:
    """'P0143' → 'motor e câmbio, genérico'; segundo caractere 1 = código do fabricante."""
    if len(codigo) < 2 or codigo[0] not in SISTEMAS:
        return "desconhecido"
    origem = "do fabricante" if codigo[1] == "1" else "genérico"
    return f"{SISTEMAS[codigo[0]]}, {origem}"


class TelaErros:
    def __init__(self, fonte: FonteOBD) -> None:
        self.fonte = fonte
        self.ativa = False
        self.estado = "fechada"   # lendo | lista | confirmar | apagando | falha
        self.codigos: dict[str, list[Codigo]] = {t: [] for t in TIPOS_ERRO}
        self.mensagem = ""
        self._pedido: Future | None = None
        self._desde = 0.0
        self._sujo = True
        self._f_titulo = pygame.font.Font(None, 40)
        self._f_codigo = pygame.font.Font(None, 36)
        self._f_texto = pygame.font.Font(None, 24)

    # --- estado -------------------------------------------------------------------------

    def _mudar(self, estado: str, mensagem: str = "") -> None:
        self.estado, self.mensagem, self._sujo = estado, mensagem, True

    def abrir(self) -> None:
        self.ativa = True
        self.ler()

    def fechar(self) -> None:
        self.ativa = False
        self._pedido = None
        self._mudar("fechada")

    def ler(self) -> None:
        self._pedido, self._desde = self.fonte.ler_erros(), time.monotonic()
        self._mudar("lendo", "Lendo os códigos do carro...")

    def _total(self) -> int:
        return sum(len(v) for v in self.codigos.values())

    def tecla(self, tecla: int) -> bool:
        """Trata a tecla; devolve True se a tela ficou fechada (o painel volta)."""
        if tecla == pygame.K_e:
            self.fechar()
            return True
        if self.estado == "confirmar":
            if tecla == pygame.K_s:
                self._pedido, self._desde = self.fonte.apagar_erros(), time.monotonic()
                self._mudar("apagando", "Apagando...")
            elif tecla == pygame.K_n:
                self._mudar("lista")
        elif self.estado in ("lista", "falha"):
            if tecla == pygame.K_l:
                self.ler()
            elif tecla == pygame.K_a and self.estado == "lista" and self._total():
                self._mudar("confirmar")
        return False

    def verificar(self) -> None:
        """Chamado a cada quadro: recolhe a resposta do pedido em andamento."""
        f = self._pedido
        if f is None:
            return
        if not f.done():
            if time.monotonic() - self._desde > ESPERA_MAX_S:
                self._pedido = None
                self._mudar("falha", "O carro não respondeu.")
            return
        self._pedido = None
        erro = f.exception()
        if erro is not None:
            self._mudar("falha", str(erro) or type(erro).__name__)
        elif self.estado == "lendo":
            self.codigos = f.result()
            self._mudar("lista")
        elif self.estado == "apagando":
            if f.result():
                self.ler()
                self.mensagem = "Códigos apagados. Lendo de novo..."
            else:
                self._mudar("falha", "A central recusou. Desligue o motor, deixe a ignição "
                                     "ligada e tente de novo.")

    # --- desenho ------------------------------------------------------------------------

    def desenhar(self, tela: pygame.Surface) -> list[pygame.Rect] | None:
        """None quando redesenhou a tela inteira; [] quando nada mudou."""
        self.verificar()
        if not self._sujo:
            return []
        self._sujo = False
        tela.fill(COR_FUNDO)
        self._texto(tela, self._f_titulo, "Códigos de erro (OBD-II)", COR_TITULO, (24, 18))
        y = 70
        if self.estado in ("lendo", "apagando", "falha"):
            cor = COR_ERRO if self.estado == "falha" else COR_TEXTO
            self._texto(tela, self._f_codigo, self.mensagem, cor, (24, y))
        elif self.estado == "confirmar":
            self._confirmacao(tela, y)
        else:
            self._lista(tela, y)
        self._texto(tela, self._f_texto, self._rodape(), COR_FRACO, (24, ALTURA - 34))
        return None

    def _rodape(self) -> str:
        if self.estado == "confirmar":
            return "S = apagar     N = cancelar     E = voltar ao painel"
        if self.estado == "lista" and self._total():
            return "L = ler de novo     A = apagar os códigos     E = voltar ao painel"
        return "L = ler de novo     E = voltar ao painel"

    def _lista(self, tela: pygame.Surface, y: int) -> None:
        if not self._total():
            self._texto(tela, self._f_codigo, "Nenhum código de erro.", COR_OK, (24, y))
            self._texto(tela, self._f_texto, "A central do motor não registrou falhas.",
                        COR_FRACO, (24, y + 40))
            return
        linhas = 0
        for tipo in TIPOS_ERRO:
            codigos = self.codigos.get(tipo, [])
            if not codigos:
                continue
            titulo = ("Armazenados (acendem a luz da injeção)" if tipo == "armazenados"
                      else "Pendentes (vistos uma vez, ainda sem luz)")
            self._texto(tela, self._f_texto, titulo, COR_TITULO, (24, y))
            y += 28
            for codigo, descricao in codigos:
                if linhas == MAX_LINHAS:
                    self._texto(tela, self._f_texto, f"... e mais {self._total() - linhas}",
                                COR_FRACO, (24, y))
                    return
                self._texto(tela, self._f_codigo, codigo, COR_ERRO, (24, y))
                self._texto(tela, self._f_texto, sistema(codigo), COR_FRACO, (130, y))
                self._texto(tela, self._f_texto, descricao or "(descrição não disponível)",
                            COR_TEXTO, (130, y + 20), largura=LARGURA - 154)
                y += 46
                linhas += 1
            y += 6

    def _confirmacao(self, tela: pygame.Surface, y: int) -> None:
        n = self._total()
        self._texto(tela, self._f_codigo, f"Apagar {n} código{'s' if n > 1 else ''}?",
                    COR_TEXTO, (24, y))
        avisos = (
            "A luz da injeção apaga, mas o defeito continua lá: se ele existir, volta.",
            "A central também zera os testes de emissão (o carro reaprende rodando).",
            "Faça com o motor desligado e a ignição ligada.",
        )
        for i, a in enumerate(avisos):
            self._texto(tela, self._f_texto, a, COR_FRACO, (24, y + 50 + i * 28))

    def _texto(self, tela: pygame.Surface, fonte: pygame.font.Font, s: str,
               cor: tuple[int, int, int], pos: tuple[int, int],
               largura: int = LARGURA - 48) -> None:
        img = fonte.render(s, True, cor)
        if img.get_width() > largura:                 # corta com reticências
            while s and fonte.size(s + "...")[0] > largura:
                s = s[:-1]
            img = fonte.render(s + "...", True, cor)
        tela.blit(img, pos)
