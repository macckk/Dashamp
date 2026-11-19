"""Temas do painel (F2.5): `painel/temas/<nome>/tema.json` + PNGs da mesma pasta.

Formato (versão 1). Cores: "#rrggbb" ou [r, g, b]. Posições em pixels da tela de 800×480.

    {
      "versao": 1,
      "nome": "Digital anos 80",
      "fundo": {"cor": "#0a0a0e", "imagem": "fundo.png"},          // imagem opcional
      "imagens": [{"arquivo": "moldura.png", "pos": [0, 0]}],     // enfeites estáticos
      "textos": [{"texto": "km/h", "pos": [700, 110], "tamanho": 22, "cor": "#9696a0",
                  "alinhar": "esquerda" | "centro" | "direita"}],
      "widgets": [
        {"tipo": "ponteiro", "canal": "rpm", "faixa": [0, 8000], "centro": [220, 240],
         "raio": 200, "zonas": [[6000, 8000, "#e62820"]], "passo_maior": 1000, ...},
        ...
      ]
    }

Tipos de widget e campos: veja `CAMPOS` (cada campo vira o parâmetro de mesmo nome do widget).
Comuns: `tipo`, `canal` (do catálogo `CANAIS`), `faixa` [mín, máx] (a luz não usa), `zonas`
[[de, até, cor], ...] e `tau` (suavização, s). O fundo (cor + imagens + textos + partes estáticas
dos widgets) é composto uma vez na carga.

Todos os erros do arquivo são juntados numa `ErroTema`, com o caminho de cada campo
(`widgets[2].raio: ...`), para o autor do tema corrigir tudo de uma vez.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pygame

from painel.fontes.base import CANAIS
from painel.widgets import Barra, Digitos, Historico, LuzEspia, Painel, Ponteiro, Widget, Zona

PASTA_TEMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temas")
VERSAO = 1
LARGURA, ALTURA = 800, 480


class ErroTema(Exception):
    def __init__(self, arquivo: str, erros: list[str]) -> None:
        self.arquivo, self.erros = arquivo, erros
        n = len(erros)
        super().__init__(f"tema inválido: {arquivo}\n{n} erro{'s' if n > 1 else ''}:\n"
                         + "\n".join(f"  - {e}" for e in erros))


class _Invalido(Exception):
    """Erro de um campo; a mensagem diz o que se esperava."""


# --- validadores de campo -------------------------------------------------------------
# Cada um recebe o valor do JSON (e o contexto) e devolve o valor pronto, ou levanta _Invalido.


def _descrever(v: Any) -> str:
    nomes = {str: "texto", bool: "verdadeiro/falso", list: "lista", dict: "objeto",
             type(None): "null"}
    tipo = "número" if isinstance(v, (int, float)) and not isinstance(v, bool) else \
        nomes.get(type(v), type(v).__name__)
    s = json.dumps(v, ensure_ascii=False)
    return f"{tipo} {s if len(s) <= 30 else s[:27] + '...'}"


def _numero(v: Any, _: Any = None) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise _Invalido(f"esperado um número, veio {_descrever(v)}")
    return float(v)


def _inteiro(v: Any, _: Any = None) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise _Invalido(f"esperado um número inteiro, veio {_descrever(v)}")
    return v


def _positivo(v: Any, _: Any = None) -> int:
    n = _inteiro(v)
    if n <= 0:
        raise _Invalido(f"deve ser maior que zero, veio {n}")
    return n


def _booleano(v: Any, _: Any = None) -> bool:
    if not isinstance(v, bool):
        raise _Invalido(f"esperado true ou false, veio {_descrever(v)}")
    return v


def _texto(v: Any, _: Any = None) -> str:
    if not isinstance(v, str):
        raise _Invalido(f"esperado um texto, veio {_descrever(v)}")
    return v


def _cor(v: Any, _: Any = None) -> tuple[int, int, int]:
    if isinstance(v, str) and len(v) == 7 and v.startswith("#"):
        try:
            return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
        except ValueError:
            pass
    elif isinstance(v, list) and len(v) == 3 and all(
            isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in v):
        return tuple(v)  # type: ignore[return-value]
    raise _Invalido(f'esperada uma cor "#rrggbb" ou [r, g, b] de 0 a 255, veio {_descrever(v)}')


def _lista_inteiros(n: int, nome: str) -> Callable[[Any, Any], tuple[int, ...]]:
    def validar(v: Any, _: Any = None) -> tuple[int, ...]:
        if not (isinstance(v, list) and len(v) == n and all(
                isinstance(c, int) and not isinstance(c, bool) for c in v)):
            raise _Invalido(f"esperado {nome}, veio {_descrever(v)}")
        return tuple(v)
    return validar


_ponto = _lista_inteiros(2, "[x, y] inteiros")
_retangulo = _lista_inteiros(4, "[x, y, largura, altura] inteiros")


def _faixa(v: Any, _: Any = None) -> tuple[float, float]:
    if not (isinstance(v, list) and len(v) == 2):
        raise _Invalido(f"esperado [mínimo, máximo], veio {_descrever(v)}")
    lo, hi = _numero(v[0]), _numero(v[1])
    if lo >= hi:
        raise _Invalido(f"o mínimo ({lo:g}) deve ser menor que o máximo ({hi:g})")
    return lo, hi


def _zonas(v: Any, _: Any = None) -> list[Zona]:
    if not isinstance(v, list):
        raise _Invalido(f"esperada uma lista de [de, até, cor], veio {_descrever(v)}")
    zonas = []
    for i, z in enumerate(v):
        if not (isinstance(z, list) and len(z) == 3):
            raise _Invalido(f"zona {i}: esperado [de, até, cor], veio {_descrever(z)}")
        try:
            de, ate, cor = _numero(z[0]), _numero(z[1]), _cor(z[2])
        except _Invalido as e:
            raise _Invalido(f"zona {i}: {e}") from None
        if de > ate:
            raise _Invalido(f"zona {i}: 'de' ({de:g}) maior que 'até' ({ate:g})")
        zonas.append(Zona(de, ate, cor))
    return zonas


def _png(v: Any, pasta: str) -> pygame.Surface:
    nome = _texto(v)
    caminho = os.path.join(pasta, nome)
    if not os.path.isfile(caminho):
        raise _Invalido(f"arquivo '{nome}' não encontrado na pasta do tema")
    try:
        img = pygame.image.load(caminho)
    except pygame.error as e:
        raise _Invalido(f"não consegui abrir '{nome}': {e}") from None
    return img.convert_alpha() if pygame.display.get_surface() is not None else img


# Campos por tipo: nome → (validador, obrigatório). "faixa" vira minimo/maximo do widget.
_COMUNS = {"canal": (_texto, True), "faixa": (_faixa, True), "zonas": (_zonas, False),
           "tau": (_numero, False)}
CAMPOS: dict[str, tuple[type[Widget], dict[str, tuple[Callable, bool]]]] = {
    "ponteiro": (Ponteiro, {**_COMUNS,
        "centro": (_ponto, True), "raio": (_positivo, True), "angulo_zero": (_numero, False),
        "varredura": (_numero, False), "passo_maior": (_numero, False),
        "divisor": (_numero, False), "menores": (_inteiro, False), "rotulo": (_texto, False),
        "cor_ponteiro": (_cor, False), "cor_face": (_cor, False), "cor_traco": (_cor, False),
        "cor_aro": (_cor, False), "fonte_numeros": (_texto, False), "sprite": (_png, False),
        "escala": (_booleano, False), "cubo": (_booleano, False)}),
    "barra": (Barra, {**_COMUNS,
        "ret": (_retangulo, True), "segmentos": (_positivo, False),
        "vertical": (_booleano, False), "espaco": (_inteiro, False), "cor": (_cor, False),
        "cor_apagada": (_cor, False)}),
    "digitos": (Digitos, {**_COMUNS,
        "pos": (_ponto, True), "digitos": (_positivo, True), "altura": (_positivo, True),
        "casas": (_inteiro, False), "cor": (_cor, False), "cor_apagada": (_cor, False),
        "espaco": (_numero, False)}),
    "luz": (LuzEspia, {
        "canal": (_texto, True), "zonas": (_zonas, True), "centro": (_ponto, True),
        "raio": (_positivo, True), "rotulo": (_texto, False), "piscar_hz": (_numero, False),
        "cor_apagada": (_cor, False), "cor_rotulo": (_cor, False)}),
    "historico": (Historico, {**_COMUNS,
        "ret": (_retangulo, True), "segundos": (_numero, False), "taxa": (_numero, False),
        "cor": (_cor, False), "cor_grade": (_cor, False), "espessura": (_positivo, False)}),
}
# Ordem dos parâmetros posicionais de cada construtor (o resto vai por nome).
_POSICIONAIS = {
    "ponteiro": ("canal", "centro", "raio", "minimo", "maximo"),
    "barra": ("canal", "ret", "minimo", "maximo"),
    "digitos": ("canal", "pos", "digitos", "altura", "minimo", "maximo"),
    "luz": ("canal", "centro", "raio", "zonas"),
    "historico": ("canal", "ret", "minimo", "maximo"),
}


@dataclass
class Tema:
    nome: str
    pasta: str
    painel: Painel
    segundos_carga: float


def _widget(i: int, w: Any, pasta: str, erros: list[str]) -> Widget | None:
    onde = f"widgets[{i}]"
    if not isinstance(w, dict):
        erros.append(f"{onde}: esperado um objeto {{...}}, veio {_descrever(w)}")
        return None
    tipo = w.get("tipo")
    if tipo not in CAMPOS:
        erros.append(f"{onde}: 'tipo' deve ser um de {', '.join(CAMPOS)}; veio {_descrever(tipo)}")
        return None
    classe, campos = CAMPOS[tipo]
    onde = f"{onde} ({tipo}{' ' + repr(w['canal']) if isinstance(w.get('canal'), str) else ''})"
    n_erros = len(erros)
    args: dict[str, Any] = {}
    for nome in w:
        if nome != "tipo" and nome not in campos:
            erros.append(f"{onde}: campo desconhecido '{nome}' (campos de {tipo}: "
                         f"{', '.join(campos)})")
    for nome, (validar, obrigatorio) in campos.items():
        if nome not in w:
            if obrigatorio:
                erros.append(f"{onde}: falta o campo obrigatório '{nome}'")
            continue
        try:
            args[nome] = validar(w[nome], pasta)
        except _Invalido as e:
            erros.append(f"{onde}.{nome}: {e}")
    canal = args.get("canal")
    if canal is not None and canal not in CANAIS:
        erros.append(f"{onde}.canal: canal desconhecido '{canal}'; os canais são: "
                     f"{', '.join(CANAIS)}")
    if len(erros) > n_erros:
        return None
    if "faixa" in args:
        args["minimo"], args["maximo"] = args.pop("faixa")
    posicionais = [args.pop(n) for n in _POSICIONAIS[tipo]]
    try:
        widget = classe(*posicionais, **args)
    except (ValueError, TypeError) as e:
        erros.append(f"{onde}: {e}")
        return None
    tela = pygame.Rect(0, 0, LARGURA, ALTURA)
    if not tela.contains(widget.ret):
        r = widget.ret
        erros.append(f"{onde}: sai da tela de {LARGURA}×{ALTURA} (ocupa x {r.x}..{r.right}, "
                     f"y {r.y}..{r.bottom})")
        return None
    return widget


def _decoracao(dados: dict, pasta: str, erros: list[str]) -> tuple[tuple[int, int, int],
                                                                  list[tuple[pygame.Surface, tuple[int, int]]]]:
    """Cor de fundo e a lista de (superfície, posição) a pintar no fundo, em ordem."""
    cor = (0, 0, 0)
    pintar: list[tuple[pygame.Surface, tuple[int, int]]] = []
    fundo = dados.get("fundo", {})
    if not isinstance(fundo, dict):
        erros.append(f"fundo: esperado um objeto {{...}}, veio {_descrever(fundo)}")
        fundo = {}
    for chave in fundo:
        if chave not in ("cor", "imagem"):
            erros.append(f"fundo: campo desconhecido '{chave}' (campos: cor, imagem)")
    try:
        cor = _cor(fundo.get("cor", "#000000"))
    except _Invalido as e:
        erros.append(f"fundo.cor: {e}")
    if "imagem" in fundo:
        try:
            pintar.append((_png(fundo["imagem"], pasta), (0, 0)))
        except _Invalido as e:
            erros.append(f"fundo.imagem: {e}")
    for i, img in enumerate(dados.get("imagens", [])):
        try:
            if not isinstance(img, dict):
                raise _Invalido(f"esperado um objeto {{...}}, veio {_descrever(img)}")
            pintar.append((_png(img.get("arquivo"), pasta), _ponto(img.get("pos", [0, 0]))))
        except _Invalido as e:
            erros.append(f"imagens[{i}]: {e}")
    fontes: dict[int, pygame.font.Font] = {}
    for i, t in enumerate(dados.get("textos", [])):
        try:
            if not isinstance(t, dict):
                raise _Invalido(f"esperado um objeto {{...}}, veio {_descrever(t)}")
            texto = _texto(t.get("texto"))
            x, y = _ponto(t.get("pos"))
            tamanho = _positivo(t.get("tamanho", 22))
            cor_t = _cor(t.get("cor", "#c8c8c8"))
            alinhar = t.get("alinhar", "esquerda")
            if alinhar not in ("esquerda", "centro", "direita"):
                raise _Invalido(f"'alinhar' deve ser esquerda, centro ou direita; veio "
                                f"{_descrever(alinhar)}")
        except _Invalido as e:
            erros.append(f"textos[{i}]: {e}")
            continue
        if tamanho not in fontes:
            fontes[tamanho] = pygame.font.Font(None, tamanho)
        img = fontes[tamanho].render(texto, True, cor_t)
        dx = {"esquerda": 0, "centro": img.get_width() // 2, "direita": img.get_width()}[alinhar]
        pintar.append((img, (x - dx, y)))
    return cor, pintar


def carregar(nome_ou_pasta: str) -> Tema:
    """Carrega pelo nome (pasta em `painel/temas/`) ou por um caminho de pasta."""
    t0 = time.perf_counter()
    pasta = nome_ou_pasta if os.path.isdir(nome_ou_pasta) else \
        os.path.join(PASTA_TEMAS, nome_ou_pasta)
    arquivo = os.path.join(pasta, "tema.json")
    if not os.path.isfile(arquivo):
        disponiveis = ", ".join(listar()) or "nenhum"
        raise ErroTema(arquivo, [f"tema '{nome_ou_pasta}' não encontrado (temas: {disponiveis})"])
    try:
        with open(arquivo, encoding="utf-8") as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        raise ErroTema(arquivo, [f"JSON inválido na linha {e.lineno}, coluna {e.colno}: {e.msg}"]) \
            from None
    except UnicodeDecodeError:
        raise ErroTema(arquivo, ["o arquivo não está em UTF-8"]) from None
    if not isinstance(dados, dict):
        raise ErroTema(arquivo, [f"o arquivo deve ser um objeto {{...}}, veio {_descrever(dados)}"])

    erros: list[str] = []
    if dados.get("versao") != VERSAO:
        erros.append(f"versao: este Dashamp lê a versão {VERSAO}, veio {_descrever(dados.get('versao'))}")
    for chave in dados:
        if chave not in ("versao", "nome", "fundo", "imagens", "textos", "widgets"):
            erros.append(f"campo desconhecido '{chave}' (campos: versao, nome, fundo, imagens, "
                         "textos, widgets)")
    nome = dados.get("nome", os.path.basename(os.path.normpath(pasta)))
    if not isinstance(nome, str):
        erros.append(f"nome: esperado um texto, veio {_descrever(nome)}")
    for chave in ("imagens", "textos"):
        if not isinstance(dados.get(chave, []), list):
            erros.append(f"{chave}: esperada uma lista [...], veio {_descrever(dados[chave])}")
            dados[chave] = []
    lista = dados.get("widgets")
    if not isinstance(lista, list) or not lista:
        erros.append(f"widgets: esperada uma lista com pelo menos um widget, veio "
                     f"{_descrever(lista)}")
        lista = []
    cor, pintar = _decoracao(dados, pasta, erros)
    widgets = [w for i, item in enumerate(lista) if (w := _widget(i, item, pasta, erros))]
    if erros:
        raise ErroTema(arquivo, erros)

    def decorar(fundo: pygame.Surface) -> None:
        for img, pos in pintar:
            fundo.blit(img, pos)

    painel = Painel((LARGURA, ALTURA), widgets, cor_fundo=cor, decorar=decorar)
    return Tema(str(nome), pasta, painel, time.perf_counter() - t0)


def listar() -> list[str]:
    if not os.path.isdir(PASTA_TEMAS):
        return []
    return sorted(n for n in os.listdir(PASTA_TEMAS)
                  if os.path.isfile(os.path.join(PASTA_TEMAS, n, "tema.json")))
