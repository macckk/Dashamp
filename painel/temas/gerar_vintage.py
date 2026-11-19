"""Gera o tema `vintage` (F2.6): dois mostradores creme com aro cromado, numeração serifada
(DejaVu Serif) e ponteiro vermelho; combustível e temperatura em mostradores pequenos dentro
dos grandes, como nos painéis antigos. Fundo de couro escuro.

    python -m painel.temas.gerar_vintage
"""
from __future__ import annotations

from painel.temas import desenho as d

CREME, CREME_BORDA = (240, 232, 208), (214, 202, 170)
TINTA = (38, 30, 24)
VERMELHO = (196, 30, 24)
AGULHA = (205, 32, 22)
COURO_TOPO, COURO_BASE = (52, 36, 28), (26, 18, 14)

# Geometria (1×). Os mesmos números vão para o tema.json.
VEL = {"c": (205, 248), "r": 190, "lo": 0, "hi": 220}
RPM = {"c": (595, 248), "r": 190, "lo": 0, "hi": 8000}
SUB_ZERO, SUB_VARREDURA = 140.0, 100.0          # submostradores: arco de 100° embaixo
COMB = {"c": (205, 352), "r": 58, "lo": 0, "hi": 100}
TEMP = {"c": (595, 352), "r": 58, "lo": 50, "hi": 130}


def _mostrador(t: d.Tela2x, m: dict) -> None:
    c, r = m["c"], m["r"]
    t.circulo((c[0] + 3, c[1] + 5), r + 2, (12, 8, 6))                  # sombra
    t.bisel(c, r, 13, (235, 235, 238), (70, 70, 76))
    t.circulo(c, r - 13, (40, 40, 44))
    t.gradiente_radial(c, r - 15, CREME, CREME_BORDA)


def _submostrador(t: d.Tela2x, m: dict, rotulos: tuple[str, str], titulo: str,
                  zona: tuple[float, float] | None, f_rot) -> None:
    c, r = m["c"], m["r"]
    lo, hi = m["lo"], m["hi"]
    if zona:
        d.zona(t, c, r, r - 7, lo, hi, *zona, VERMELHO, SUB_ZERO, SUB_VARREDURA)
    d.escala(t, c, r, lo, hi, passo_maior=(hi - lo) / 4, menores=1, divisor=1, f=None, cor=TINTA,
             zero=SUB_ZERO, varredura=SUB_VARREDURA, comp_maior=0.2, comp_menor=0.11,
             larg_maior=2.2, larg_menor=1.2)
    t.texto(f_rot, rotulos[0], TINTA, d.ponto(c, SUB_ZERO + 8, r * 0.62))
    t.texto(f_rot, rotulos[1], TINTA, d.ponto(c, SUB_ZERO - SUB_VARREDURA - 8, r * 0.62))
    t.texto(f_rot, titulo, TINTA, (c[0], c[1] + r * 0.36))     # embaixo: o ponteiro não passa


def gerar() -> None:
    d.iniciar()
    t = d.Tela2x()
    t.gradiente_vertical(COURO_TOPO, COURO_BASE)
    t.granulado(6, semente=7, densidade=0.25)
    serifa = d.fonte("DejaVuSerif-Bold.ttf", 25 * d.E)
    serifa_vel = d.fonte("DejaVuSerif-Bold.ttf", 19 * d.E)      # 12 números: fonte menor
    serifa_peq = d.fonte("DejaVuSerif.ttf", 13 * d.E)
    italico = d.fonte("DejaVuSerif.ttf", 15 * d.E)

    for m in (VEL, RPM):
        _mostrador(t, m)
    # Velocímetro: 0–220 de 20 em 20, traço menor a cada 10.
    d.escala(t, VEL["c"], VEL["r"] - 22, 0, 220, passo_maior=20, menores=1, divisor=1,
             f=serifa_vel, cor=TINTA, r_numeros=0.76)
    t.texto(italico, "km/h", TINTA, (VEL["c"][0], VEL["c"][1] - 62))
    # Conta-giros: 0–8 ×1000, faixa vermelha de 6500 em diante.
    d.zona(t, RPM["c"], RPM["r"] - 22, RPM["r"] - 34, 0, 8000, 6500, 8000, VERMELHO)
    d.escala(t, RPM["c"], RPM["r"] - 22, 0, 8000, passo_maior=1000, menores=3, divisor=1000,
             f=serifa, cor=TINTA, r_numeros=0.74)
    t.texto(italico, "rpm × 1000", TINTA, (RPM["c"][0], RPM["c"][1] - 62))
    _submostrador(t, COMB, ("E", "F"), "COMB.", (0, 12), serifa_peq)
    _submostrador(t, TEMP, ("C", "H"), "TEMP.", (110, 130), serifa_peq)
    for x, rot in ((30, "TROCA"), (770, "BATERIA")):                    # rótulos das luzes
        t.texto(serifa_peq, rot, (190, 170, 140), (x, 452))
    t.texto(d.fonte("DejaVuSerif-Bold.ttf", 12 * d.E), "D A S H A M P", (150, 128, 100), (400, 462))
    fundo = t.reduzir()

    agulha = d.agulha(158, 7, AGULHA)
    agulha_peq = d.agulha(48, 4, AGULHA, cauda=0.15)
    comum = {"escala": False, "cor_ponteiro": d.hexa(AGULHA)}
    tema = {
        "versao": 1,
        "nome": "Vintage",
        "fundo": {"cor": d.hexa(COURO_BASE), "imagem": "fundo.png"},
        "widgets": [
            {"tipo": "ponteiro", "canal": "velocidade", "faixa": [0, 220],
             "centro": list(VEL["c"]), "raio": VEL["r"] - 15, "sprite": "agulha.png", **comum},
            {"tipo": "ponteiro", "canal": "combustivel_nivel", "faixa": [0, 100],
             "centro": list(COMB["c"]), "raio": COMB["r"], "angulo_zero": SUB_ZERO,
             "varredura": SUB_VARREDURA, "sprite": "agulha_pequena.png", "tau": 0.5, **comum},
            {"tipo": "ponteiro", "canal": "rpm", "faixa": [0, 8000], "centro": list(RPM["c"]),
             "raio": RPM["r"] - 15, "sprite": "agulha.png", **comum},
            {"tipo": "ponteiro", "canal": "temp_motor", "faixa": [50, 130],
             "centro": list(TEMP["c"]), "raio": TEMP["r"], "angulo_zero": SUB_ZERO,
             "varredura": SUB_VARREDURA, "sprite": "agulha_pequena.png", "tau": 0.5, **comum},
            {"tipo": "luz", "canal": "rpm", "centro": [30, 425], "raio": 11,
             "zonas": [[6500, 9000, "#ff3020"]], "piscar_hz": 5},
            {"tipo": "luz", "canal": "tensao", "centro": [770, 425], "raio": 11,
             "zonas": [[0, 12.2, "#ffb000"]]},
        ],
    }
    d.salvar("vintage", tema, {"fundo.png": fundo, "agulha.png": agulha,
                               "agulha_pequena.png": agulha_peq})


if __name__ == "__main__":
    gerar()
