"""Testes do formato de tema (F2.5), com o display "dummy" do SDL."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pygame
import pytest

from painel import tema as tm
from painel.widgets import Barra, Digitos, Historico, LuzEspia, Ponteiro


@pytest.fixture(autouse=True)
def tela():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()
    yield pygame.display.set_mode((800, 480))
    pygame.display.quit()


def _tema(pasta: Path, dados: dict | str) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    texto = dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False)
    (pasta / "tema.json").write_text(texto, encoding="utf-8")
    return pasta


def _minimo(**extra) -> dict:
    d = {"versao": 1, "nome": "T", "widgets": [
        {"tipo": "barra", "canal": "rpm", "faixa": [0, 8000], "ret": [10, 10, 200, 20]}]}
    d.update(extra)
    return d


def _erros(pasta: Path) -> list[str]:
    with pytest.raises(tm.ErroTema) as e:
        tm.carregar(str(pasta))
    return e.value.erros


def test_exemplo_carrega_rapido() -> None:
    assert "exemplo" in tm.listar()
    t = tm.carregar("exemplo")
    assert t.nome == "Exemplo" and t.segundos_carga < 1.0
    tipos = [type(w) for w in t.painel.widgets]
    assert {Ponteiro, Digitos, Barra, LuzEspia, Historico} == set(tipos) and len(tipos) == 10
    assert t.painel.fundo.get_at((5, 5))[:3] == (10, 10, 14)


def test_imagens_e_textos_no_fundo(tmp_path: Path) -> None:
    img = pygame.Surface((20, 20))
    img.fill((0, 200, 0))
    pygame.image.save(img, str(tmp_path / "quadrado.png"))
    seta = pygame.Surface((60, 10), pygame.SRCALPHA)
    seta.fill((0, 0, 255), (30, 3, 30, 4))
    pygame.image.save(seta, str(tmp_path / "seta.png"))
    _tema(tmp_path, _minimo(
        fundo={"cor": [1, 2, 3]}, imagens=[{"arquivo": "quadrado.png", "pos": [700, 400]}],
        textos=[{"texto": "OI", "pos": [400, 300], "tamanho": 40, "cor": "#ffffff",
                 "alinhar": "centro"}],
        widgets=[{"tipo": "ponteiro", "canal": "rpm", "faixa": [0, 8000], "centro": [200, 200],
                  "raio": 100, "sprite": "seta.png", "escala": False, "cubo": False}]))
    t = tm.carregar(str(tmp_path))
    f = t.painel.fundo
    assert f.get_at((0, 0))[:3] == (1, 2, 3) and f.get_at((710, 410))[:3] == (0, 200, 0)
    assert any(f.get_at((x, y))[:3] == (255, 255, 255) for x in range(380, 420)
               for y in range(300, 330))
    p = t.painel.widgets[0]
    assert p.cache.sprite.get_size() == (60, 10)
    assert f.get_at((200, 150))[:3] == (1, 2, 3)      # escala=false: face não desenhada


@pytest.mark.parametrize("dados, trecho", [
    ('{"versao": 1,\n "widgets": [}', "JSON inválido na linha 2"),
    (_minimo(versao=2), "versão 1, veio número 2"),
    (_minimo(cor="#fff"), "campo desconhecido 'cor'"),
    (_minimo(widgets=[]), "pelo menos um widget"),
    (_minimo(fundo={"cor": "vermelho"}), "fundo.cor: esperada uma cor"),
    (_minimo(fundo={"imagem": "x.png"}), "'x.png' não encontrado"),
    (_minimo(textos=[{"texto": 3, "pos": [0, 0]}]), "textos[0]: esperado um texto"),
    (_minimo(widgets=[{"tipo": "barra", "canal": "rpm", "faixa": [0, 1],
                       "ret": [700, 10, 200, 20]}]), "sai da tela de 800×480"),
    (_minimo(widgets=[{"tipo": "barra", "canal": "rmp", "faixa": [0, 1],
                       "ret": [0, 0, 10, 10]}]), "canal desconhecido 'rmp'"),
    (_minimo(widgets=[{"tipo": "barra", "canal": "rpm", "faixa": [0, 1]}]),
     "falta o campo obrigatório 'ret'"),
    (_minimo(widgets=[{"tipo": "barra", "canal": "rpm", "faixa": [0, 1], "ret": [0, 0, 10, 10],
                       "segmentos": 2.5}]), "segmentos: esperado um número inteiro"),
    (_minimo(widgets=[{"tipo": "barra", "canal": "rpm", "faixa": [0, 1], "ret": [0, 0, 10, 10],
                       "zonas": [[0, 1, "#ff00"]]}]), "zonas: zona 0: esperada uma cor"),
    (_minimo(widgets=[{"tipo": "digitos", "canal": "rpm", "faixa": [0, 1], "pos": [0, 0],
                       "digitos": 0, "altura": 10}]), "digitos: deve ser maior que zero"),
    (_minimo(widgets=[{"tipo": "agulha"}]), "'tipo' deve ser um de ponteiro, barra"),
    (_minimo(widgets=[{"tipo": "luz", "canal": "rpm", "centro": [50, 50], "raio": 5,
                       "zonas": []}]), "a luz precisa de pelo menos uma zona"),
])
def test_erros_legiveis(tmp_path: Path, dados, trecho: str) -> None:
    erros = _erros(_tema(tmp_path / "t", dados))
    assert any(trecho in e for e in erros), erros


def test_junta_todos_os_erros(tmp_path: Path) -> None:
    pasta = _tema(tmp_path / "t", {"versao": 1, "fundo": {"cor": "x"}, "widgets": [
        {"tipo": "barra", "canal": "rmp", "faixa": [5, 1], "ret": [0, 0, 1, 1]},
        {"tipo": "ponteiro", "canal": "rpm", "faixa": [0, 1], "centro": [0, 0]}]})
    with pytest.raises(tm.ErroTema) as e:
        tm.carregar(str(pasta))
    assert len(e.value.erros) == 4
    texto = str(e.value)
    assert texto.startswith("tema inválido: ") and "4 erros:" in texto
    assert "widgets[0] (barra 'rmp').faixa" in texto and "widgets[1] (ponteiro 'rpm')" in texto


def test_tema_inexistente_lista_os_disponiveis() -> None:
    with pytest.raises(tm.ErroTema, match="temas: .*exemplo"):
        tm.carregar("nao_existe")


@pytest.mark.parametrize("nome, tipos", [
    ("vintage", {"Ponteiro", "LuzEspia"}),
    ("digital80", {"Barra", "Digitos", "LuzEspia"}),
    ("moderno", {"Arco", "Numero", "LuzEspia"}),
])
def test_tres_temas_do_projeto(nome: str, tipos: set[str]) -> None:
    t = tm.carregar(nome)
    assert t.segundos_carga < 1.0
    assert {type(w).__name__ for w in t.painel.widgets} == tipos
    assert os.path.isfile(os.path.join(t.pasta, "fundo.png"))
    # O fundo veio da imagem (não é a cor lisa).
    f = t.painel.fundo
    assert len({tuple(f.get_at((x, 240))) for x in range(0, 800, 20)}) > 3
