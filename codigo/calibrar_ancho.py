#!/usr/bin/env python3
"""
Imprime una regla a lo ancho de todo el cabezal (576 dots = 80mm) para
saber que parte cae sobre el papel cuando se usa un rollo mas angosto.
Con el numero mas pequeno y el mas grande que se leen en el papel se
elige MARGEN_IZQUIERDO_PX en impresora.py, de modo que la imagen de
ANCHO_PAPEL_PX quede centrada entre ambos.

Uso:
    .venv/bin/python codigo/calibrar_ancho.py
"""

from PIL import Image, ImageDraw, ImageFont

import impresora
import servidor

PASO_PX = 48  # 6mm entre numeros
ALTO_PX = 120


def generar_regla() -> Image.Image:
    regla = Image.new("RGB", (impresora.ANCHO_CABEZAL_PX, ALTO_PX), "white")
    dibujo = ImageDraw.Draw(regla)
    fuente = ImageFont.truetype(servidor.FUENTE_REGULAR_PATH, 16)

    for x in range(0, impresora.ANCHO_CABEZAL_PX, 8):
        largo = 40 if x % PASO_PX == 0 else 15
        dibujo.line([(x, 0), (x, largo)], fill="black", width=2)

    for x in range(0, impresora.ANCHO_CABEZAL_PX, PASO_PX):
        dibujo.text((x + 3, 50), str(x), font=fuente, fill="black")

    dibujo.rectangle([0, 0, impresora.ANCHO_CABEZAL_PX - 1, ALTO_PX - 1], outline="black", width=2)
    return regla


if __name__ == "__main__":
    # La regla ya mide todo el cabezal: se imprime sin margen.
    impresora.MARGEN_IZQUIERDO_PX = 0
    impresora.imprimir_imagen(generar_regla())
    print("Regla impresa. Anota el numero mas pequeno y el mas grande que se ven en el papel.")
