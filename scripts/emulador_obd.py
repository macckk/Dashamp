"""Roda o ELM327-emulator (cenário "car") com códigos de erro simulados (testes da F3.2).

    python scripts/emulador_obd.py --erros P0143,P0300 --pendentes C0035 -- -s car -b /tmp/elm.txt

Os argumentos depois de `--` vão para o emulador. Os códigos são armazenados (modo 03) e pendentes
(modo 07); o modo 04 (apagar) os zera, como num carro. Só para testes: precisa do pacote
ELM327-emulator no venv (deploy/requirements.txt) e roda no Linux.
"""
from __future__ import annotations

import argparse
import sys

GRUPOS = {"P": 0, "C": 1, "B": 2, "U": 3}


def codigo_para_hex(codigo: str) -> str:
    """'P0143' → '0143', 'C0035' → '4035', 'U1234' → 'D234' (2 bytes da SAE J2012)."""
    c = codigo.strip().upper()
    if len(c) != 5 or c[0] not in GRUPOS or c[1] not in "0123":
        raise ValueError(f"código inválido: {codigo!r} (ex.: P0143)")
    int(c[2:], 16)                                   # os 3 últimos são hexadecimais
    primeiro = (GRUPOS[c[0]] << 2) | int(c[1])
    return f"{primeiro:X}{c[2:]}"


def main() -> None:
    if "--" in sys.argv:
        i = sys.argv.index("--")
        nossos, do_emulador = sys.argv[1:i], sys.argv[i + 1:]
    else:
        nossos, do_emulador = sys.argv[1:], ["-s", "car"]
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--erros", default="", help="códigos armazenados, separados por vírgula")
    p.add_argument("--pendentes", default="", help="códigos pendentes, separados por vírgula")
    a = p.parse_args(nossos)

    from elm import obd_message                     # noqa: PLC0415 — só existe com o emulador
    from elm.interpreter import main as emulador    # noqa: PLC0415

    # O emulador 4.0.0 responde "43 DTC DTC..." sem o byte com a quantidade de códigos que a
    # SAE J1979 manda no CAN ("43 03 DTC DTC DTC"); o python-OBD (e uma central de verdade) usa o
    # byte, e lia "43 01 43 ..." como um código só ("C0303"). Aqui a resposta sai como a da norma.
    def dtc_frames_com_quantidade(emulator, dtc_list, sid, header=obd_message.ECU_R_ADDR_E):
        codigos = [] if emulator.counters.get("cmd_dtc_cleared") else [d for d in dtc_list if d]
        dados = [sid, f"{len(codigos):02X}"]
        for d in codigos:
            dados += [d[0:2], d[2:4]]
        return obd_message.iso_tp_frames(dados, header)

    obd_message.dtc_frames = dtc_frames_com_quantidade
    obd_message.DTC_STORED[:] = [codigo_para_hex(c) for c in a.erros.split(",") if c]
    obd_message.DTC_PENDING[:] = [codigo_para_hex(c) for c in a.pendentes.split(",") if c]
    sys.argv = ["elm", *do_emulador]
    emulador()


if __name__ == "__main__":
    main()
