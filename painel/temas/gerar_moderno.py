"""Gera o tema `moderno` (F2.6): arco minimalista de rotação com a velocidade em número grande no
centro; temperatura e combustível em arcos pequenos nos cantos. Fundo escuro em degradê.

    python -m painel.temas.gerar_moderno
"""
from __future__ import annotations

from painel.temas import desenho as d

FUNDO_TOPO, FUNDO_BASE = (20, 26, 34), (6, 8, 11)
CIANO, APAGADO = (0, 196, 255), (34, 42, 52)
LARANJA, VERMELHO = (255, 150, 40), (255, 60, 50)
CINZA, CINZA_CLARO, BRANCO = (110, 122, 136), (170, 180, 192), (240, 244, 248)

RPM = {"c": (400, 262), "r": 214, "esp": 20, "zero": 210.0, "varr": 240.0}
TEMP = {"c": (92, 392), "r": 70}
COMB = {"c": (708, 392), "r": 70}
PEQ_ZERO, PEQ_VARR = 225.0, 270.0


def gerar() -> None:
    d.iniciar()
    t = d.Tela2x(FUNDO_BASE)
    # Brilho atrás do arco, esmaecendo até a cor do fundo (sem borda visível).
    t.gradiente_radial(RPM["c"], 520, FUNDO_TOPO, FUNDO_BASE, passos=120)
    sans = d.fonte("DejaVuSans.ttf", 14 * d.E)
    sans_peq = d.fonte("DejaVuSans.ttf", 11 * d.E)
    c, r = RPM["c"], RPM["r"]
    # Números 0..8 por dentro do arco e uma linha fina por fora.
    for i in range(9):
        a = d.angulo(i * 1000, 0, 8000, RPM["zero"], RPM["varr"])
        t.texto(sans, str(i), CINZA_CLARO if i < 6 else LARANJA, d.ponto(c, a, r - RPM["esp"] - 18))
        t.linha(d.ponto(c, a, r + 4), d.ponto(c, a, r + 10), CINZA, 1.2)
    t.faixa_arco(c, r + 4, r + 3, RPM["zero"], RPM["zero"] - RPM["varr"], CINZA)
    t.texto(sans, "km/h", CINZA_CLARO, (c[0], c[1] + 56))
    t.texto(sans_peq, "rpm × 1000", CINZA, (c[0], c[1] - 118))
    t.texto(sans_peq, "MARCHA", CINZA, (c[0], c[1] + 152))
    for m, rotulo in ((TEMP, "TEMP °C"), (COMB, "COMB %")):
        t.texto(sans_peq, rotulo, CINZA, (m["c"][0], m["c"][1] + 44))
    fundo = t.reduzir()

    tema = {
        "versao": 1,
        "nome": "Moderno",
        "fundo": {"cor": d.hexa(FUNDO_BASE), "imagem": "fundo.png"},
        "widgets": [
            {"tipo": "arco", "canal": "rpm", "faixa": [0, 8000], "centro": list(c), "raio": r,
             "espessura": RPM["esp"], "angulo_zero": RPM["zero"], "varredura": RPM["varr"],
             "segmentos": 64, "espaco": 1.0, "tau": 0.08, "cor": d.hexa(CIANO),
             "cor_apagada": d.hexa(APAGADO),
             "zonas": [[5500, 6500, d.hexa(LARANJA)], [6500, 8000, d.hexa(VERMELHO)]]},
            {"tipo": "numero", "canal": "velocidade", "faixa": [0, 260], "centro": [c[0], c[1] - 8],
             "tamanho": 150, "digitos": 3, "tau": 0.25, "cor": d.hexa(BRANCO)},
            {"tipo": "numero", "canal": "marcha", "faixa": [0, 6], "centro": [c[0], c[1] + 118],
             "tamanho": 56, "digitos": 1, "tau": 0, "cor": d.hexa(CIANO)},
            {"tipo": "arco", "canal": "temp_motor", "faixa": [50, 130], "centro": list(TEMP["c"]),
             "raio": TEMP["r"], "espessura": 8, "angulo_zero": PEQ_ZERO, "varredura": PEQ_VARR,
             "segmentos": 32, "espaco": 1.5, "tau": 0.5, "cor": d.hexa(CIANO),
             "cor_apagada": d.hexa(APAGADO), "zonas": [[105, 130, d.hexa(VERMELHO)]]},
            {"tipo": "numero", "canal": "temp_motor", "faixa": [-40, 150],
             "centro": list(TEMP["c"]), "tamanho": 40, "digitos": 3, "tau": 0.5,
             "cor": d.hexa(BRANCO), "zonas": [[105, 150, d.hexa(VERMELHO)]]},
            {"tipo": "arco", "canal": "combustivel_nivel", "faixa": [0, 100],
             "centro": list(COMB["c"]), "raio": COMB["r"], "espessura": 8,
             "angulo_zero": PEQ_ZERO, "varredura": PEQ_VARR, "segmentos": 32, "espaco": 1.5,
             "tau": 0.5, "cor": d.hexa(CIANO), "cor_apagada": d.hexa(APAGADO),
             "zonas": [[0, 12, d.hexa(VERMELHO)]]},
            {"tipo": "numero", "canal": "combustivel_nivel", "faixa": [0, 100],
             "centro": list(COMB["c"]), "tamanho": 40, "digitos": 3, "tau": 0.5,
             "cor": d.hexa(BRANCO), "zonas": [[0, 12, d.hexa(VERMELHO)]]},
            {"tipo": "luz", "canal": "rpm", "centro": [40, 40], "raio": 10,
             "zonas": [[6500, 9000, d.hexa(VERMELHO)]], "piscar_hz": 6},
        ],
    }
    d.salvar("moderno", tema, {"fundo.png": fundo})


if __name__ == "__main__":
    gerar()
