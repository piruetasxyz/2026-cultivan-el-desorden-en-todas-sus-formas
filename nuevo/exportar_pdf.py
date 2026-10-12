#!/usr/bin/env python3
"""
Exporta los mensajes del archivo (archivo/mensajes.jsonl) a un PDF, una
pagina por recibo, con el mismo tamano, tipografia y cortes de linea que
los recibos impresos. El texto queda vectorial: nitido, buscable y
copiable.

Uso:
    .venv/bin/python nuevo/exportar_pdf.py                  # todos
    .venv/bin/python nuevo/exportar_pdf.py 3 7 12           # solo esos numeros
    .venv/bin/python nuevo/exportar_pdf.py --ultimos 10     # los ultimos 10
    .venv/bin/python nuevo/exportar_pdf.py --salida otro.pdf
"""

import argparse
import os
import sys

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import impresora
import servidor

SALIDA_POR_DEFECTO = os.path.join(os.path.dirname(servidor.ARCHIVO_PATH), "mensajes.pdf")
MM_POR_DOT = 1 / 8  # la impresora imprime 8 dots por milimetro


def exportar(mensajes: list[dict], salida: str) -> None:
    pdfmetrics.registerFont(TTFont("SpaceMono", servidor.FUENTE_REGULAR_PATH))
    ancho_px = impresora.ANCHO_PAPEL_PX
    alto_px = servidor.ALTO_RECIBO_PX

    pdf = canvas.Canvas(salida, pagesize=(ancho_px * MM_POR_DOT * mm, alto_px * MM_POR_DOT * mm))
    pdf.setTitle("Archivo de mensajes")
    for mensaje in mensajes:
        # Se trabaja en dots de la impresora, igual que renderizar_texto.
        pdf.scale(MM_POR_DOT * mm, MM_POR_DOT * mm)
        fuente, alto_linea, lineas = servidor.componer_texto(mensaje["texto"])
        ascendente = fuente.getmetrics()[0]
        pdf.setFont("SpaceMono", fuente.size)
        for i, linea in enumerate(lineas):
            # Pillow ubica el texto por arriba (ascendente) y reportlab por
            # la linea base, con el eje y hacia arriba.
            linea_base = servidor.PADDING + i * alto_linea + ascendente
            pdf.drawString(servidor.PADDING, alto_px - linea_base, linea)
        pdf.showPage()
    pdf.save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta mensajes del archivo a PDF.")
    parser.add_argument("numeros", nargs="*", type=int, help="numeros de mensaje (por defecto, todos)")
    parser.add_argument("--ultimos", type=int, metavar="N", help="exporta los ultimos N mensajes")
    parser.add_argument("--salida", default=SALIDA_POR_DEFECTO, help="ruta del PDF")
    args = parser.parse_args()

    mensajes = servidor.leer_archivo()
    if not mensajes:
        print(f"El archivo esta vacio o no existe: {servidor.ARCHIVO_PATH}")
        return

    if args.ultimos:
        mensajes = mensajes[-args.ultimos:]
    elif args.numeros:
        fuera = [n for n in args.numeros if not 1 <= n <= len(mensajes)]
        if fuera:
            sys.exit(f"Numeros fuera de rango (hay {len(mensajes)} mensajes): {fuera}")
        mensajes = [mensajes[n - 1] for n in args.numeros]

    exportar(mensajes, args.salida)
    print(f"{len(mensajes)} recibos exportados a {args.salida}")


if __name__ == "__main__":
    main()
