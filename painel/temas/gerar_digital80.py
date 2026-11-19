"""Gera o tema `digital80` (F2.6): painel digital dos anos 80. Conta-giros em bargraph
verde/âmbar/vermelho, velocidade e marcha em dígitos de LED, barras verticais de temperatura e
combustível, consumo e tensão. Fundo preto com molduras finas e rótulos em âmbar.

    python -m painel.temas.gerar_digital80
"""
from __future__ import annotations

from painel.temas import desenho as d

PRETO = (8, 8, 10)
MOLDURA = (52, 56, 60)
AMBAR = (255, 168, 30)
AMBAR_ESCURO = (150, 96, 20)
VERDE, VERDE_APAGADO = (60, 255, 90), (16, 40, 20)
LARANJA, VERMELHO = (255, 170, 0), (255, 40, 30)
LED_VEL, LED_VEL_APAGADO = (255, 60, 30), (42, 14, 10)

RPM_BARRA = (40, 58, 720, 54)             # x, y, largura, altura
TEMP_BARRA = (36, 168, 34, 236)
COMB_BARRA = (730, 168, 34, 236)
ACEL_BARRA = (130, 420, 540, 14)


def _moldura(t: d.Tela2x, ret: tuple[int, int, int, int], titulo: str, f) -> None:
    x, y, w, h = ret
    t.retangulo((x - 6, y - 6, w + 12, h + 12), MOLDURA, 1, raio=4)
    if titulo:
        largura = f.size(titulo)[0] / d.E + 10
        t.retangulo((x + 8, y - 12, largura, 12), PRETO)
        t.texto(f, titulo, AMBAR, (x + 13, y - 6), "midleft")


def gerar() -> None:
    d.iniciar()
    t = d.Tela2x(PRETO)
    for y in range(0, d.ALTURA * d.E, 4):                 # linhas de varredura discretas
        t.s.fill((13, 13, 16), (0, y, d.LARGURA * d.E, 1))
    rot = d.fonte("DejaVuSansMono-Bold.ttf", 11 * d.E)
    rot_grande = d.fonte("DejaVuSansMono-Bold.ttf", 16 * d.E)

    # Conta-giros: escala 0..8 embaixo da barra.
    _moldura(t, RPM_BARRA, "RPM x1000", rot)
    x, y, w, h = RPM_BARRA
    for i in range(9):
        xi = x + w * i / 8
        t.linha((xi, y + h + 4), (xi, y + h + 10), AMBAR_ESCURO, 1.5)
        t.texto(rot, str(i), AMBAR, (xi, y + h + 19))
    # Velocidade e marcha.
    _moldura(t, (150, 160, 400, 196), "VELOCIDADE", rot)
    t.texto(rot_grande, "KM/H", AMBAR, (548, 345), "bottomright")
    _moldura(t, (590, 160, 110, 196), "MARCHA", rot)
    # Barras verticais.
    _moldura(t, TEMP_BARRA, "", rot)
    t.texto(rot, "TEMP", AMBAR, (TEMP_BARRA[0] + 17, TEMP_BARRA[1] - 15))
    t.texto(rot, "H", AMBAR_ESCURO, (TEMP_BARRA[0] + 47, TEMP_BARRA[1] + 6))
    t.texto(rot, "C", AMBAR_ESCURO, (TEMP_BARRA[0] + 47, TEMP_BARRA[1] + TEMP_BARRA[3] - 6))
    _moldura(t, COMB_BARRA, "", rot)
    t.texto(rot, "COMB", AMBAR, (COMB_BARRA[0] + 17, COMB_BARRA[1] - 15))
    t.texto(rot, "F", AMBAR_ESCURO, (COMB_BARRA[0] - 13, COMB_BARRA[1] + 6))
    t.texto(rot, "E", AMBAR_ESCURO, (COMB_BARRA[0] - 13, COMB_BARRA[1] + COMB_BARRA[3] - 6))
    # Consumo e tensão (dígitos pequenos) e acelerador.
    _moldura(t, (150, 374, 170, 36), "", rot)
    t.texto(rot, "L/H", AMBAR, (318, 404), "bottomright")
    _moldura(t, (380, 374, 170, 36), "", rot)
    t.texto(rot, "VOLTS", AMBAR, (548, 404), "bottomright")
    t.texto(rot, "ACEL", AMBAR, (ACEL_BARRA[0] - 10, ACEL_BARRA[1] + 7), "midright")
    t.texto(rot, "SHIFT", AMBAR, (645, 392))
    fundo = t.reduzir()

    vx, vy = RPM_BARRA[0], RPM_BARRA[1]
    tema = {
        "versao": 1,
        "nome": "Digital 80",
        "fundo": {"cor": d.hexa(PRETO), "imagem": "fundo.png"},
        "widgets": [
            {"tipo": "barra", "canal": "rpm", "faixa": [0, 8000], "ret": list(RPM_BARRA),
             "segmentos": 40, "espaco": 4, "tau": 0.06, "cor": d.hexa(VERDE),
             "cor_apagada": d.hexa(VERDE_APAGADO),
             "zonas": [[5000, 6500, d.hexa(LARANJA)], [6500, 8000, d.hexa(VERMELHO)]]},
            {"tipo": "digitos", "canal": "velocidade", "faixa": [0, 260], "pos": [172, 180],
             "digitos": 3, "altura": 150, "tau": 0.25, "cor": d.hexa(LED_VEL),
             "cor_apagada": d.hexa(LED_VEL_APAGADO)},
            {"tipo": "digitos", "canal": "marcha", "faixa": [0, 6], "pos": [610, 196],
             "digitos": 1, "altura": 120, "tau": 0, "cor": d.hexa(AMBAR),
             "cor_apagada": "#2a1c08"},
            {"tipo": "barra", "canal": "temp_motor", "faixa": [20, 130], "ret": list(TEMP_BARRA),
             "segmentos": 22, "vertical": True, "espaco": 3, "tau": 0.5, "cor": d.hexa(VERDE),
             "cor_apagada": d.hexa(VERDE_APAGADO),
             "zonas": [[20, 60, "#3c8cff"], [105, 130, d.hexa(VERMELHO)]]},
            {"tipo": "barra", "canal": "combustivel_nivel", "faixa": [0, 100],
             "ret": list(COMB_BARRA), "segmentos": 22, "vertical": True, "espaco": 3,
             "tau": 0.5, "cor": d.hexa(VERDE), "cor_apagada": d.hexa(VERDE_APAGADO),
             "zonas": [[0, 12, d.hexa(VERMELHO)]]},
            {"tipo": "digitos", "canal": "combustivel_lh", "faixa": [0, 40], "pos": [158, 380],
             "digitos": 3, "altura": 26, "casas": 1, "tau": 0.4, "cor": d.hexa(VERDE),
             "cor_apagada": d.hexa(VERDE_APAGADO)},
            {"tipo": "digitos", "canal": "tensao", "faixa": [0, 18], "pos": [388, 380],
             "digitos": 3, "altura": 26, "casas": 1, "tau": 0.4, "cor": d.hexa(VERDE),
             "cor_apagada": d.hexa(VERDE_APAGADO), "zonas": [[0, 12.2, d.hexa(LARANJA)]]},
            {"tipo": "barra", "canal": "acelerador", "faixa": [0, 100], "ret": list(ACEL_BARRA),
             "segmentos": 30, "espaco": 3, "tau": 0.06, "cor": d.hexa(AMBAR),
             "cor_apagada": "#2a1c08"},
            {"tipo": "luz", "canal": "rpm", "centro": [645, 371], "raio": 9,
             "zonas": [[6000, 9000, d.hexa(VERMELHO)]], "piscar_hz": 6},
        ],
    }
    del vx, vy
    d.salvar("digital80", tema, {"fundo.png": fundo})


if __name__ == "__main__":
    gerar()
