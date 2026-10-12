#!/usr/bin/env python3
"""
Imprime una regla a lo ancho de todo el cabezal (576 dots = 80mm) para
saber que parte cae sobre el papel cuando se usa un rollo mas angosto.
El numero mas pequeno que se alcance a leer en el papel es el valor
para MARGEN_IZQUIERDO_PX en printer_lib.py.

Uso:
    .venv/bin/python antiguo/calibrar_ancho.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

import printer_lib

ANCHO_CABEZAL_PX = 576
PASO_PX = 48  # 6mm entre numeros
ALTO_PX = 120
RUTA_REGLA = os.path.join(os.path.dirname(__file__), "regla_calibracion.png")


def generar_regla() -> str:
    regla = Image.new("RGB", (ANCHO_CABEZAL_PX, ALTO_PX), "white")
    dibujo = ImageDraw.Draw(regla)
    fuente = ImageFont.truetype(printer_lib.CODE_FONT_PATH, 16, index=0)

    for x in range(0, ANCHO_CABEZAL_PX, 8):
        largo = 40 if x % PASO_PX == 0 else 15
        dibujo.line([(x, 0), (x, largo)], fill="black", width=2)

    for x in range(0, ANCHO_CABEZAL_PX, PASO_PX):
        dibujo.text((x + 3, 50), str(x), font=fuente, fill="black")

    dibujo.rectangle([0, 0, ANCHO_CABEZAL_PX - 1, ALTO_PX - 1], outline="black", width=2)
    regla.save(RUTA_REGLA)
    return RUTA_REGLA


if __name__ == "__main__":
    printer_lib.print_image(generar_regla(), margen_px=0)
    print("Regla impresa. Anota el numero mas pequeno que se ve en el papel.")
