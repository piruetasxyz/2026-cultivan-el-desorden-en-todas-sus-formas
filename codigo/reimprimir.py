#!/usr/bin/env python3
"""
Lista y reimprime mensajes del archivo (archivo/mensajes.jsonl), con el
mismo formato que los recibos originales.

Uso:
    .venv/bin/python codigo/reimprimir.py                # lista todos, numerados
    .venv/bin/python codigo/reimprimir.py 3 7 12         # reimprime esos numeros
    .venv/bin/python codigo/reimprimir.py --ultimos 5    # reimprime los ultimos 5
    .venv/bin/python codigo/reimprimir.py --todos        # reimprime todos

Ojo: si el servidor esta imprimiendo justo en ese momento, la impresora
puede responder "Access denied". En ese caso, esperar y volver a correrlo.
"""

import argparse
import sys

import impresora
import servidor

LARGO_VISTA_PREVIA = 60


def listar(mensajes: list[dict]) -> None:
    for numero, mensaje in enumerate(mensajes, start=1):
        texto = mensaje["texto"].replace("\n", " / ")
        if len(texto) > LARGO_VISTA_PREVIA:
            texto = texto[:LARGO_VISTA_PREVIA - 1] + "…"
        print(f"{numero:4d}  {mensaje['fecha']}  {texto}")
    print(f"\n{len(mensajes)} mensajes en {servidor.ARCHIVO_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista y reimprime mensajes del archivo.")
    parser.add_argument("numeros", nargs="*", type=int, help="numeros de mensaje a reimprimir")
    parser.add_argument("--ultimos", type=int, metavar="N", help="reimprime los ultimos N mensajes")
    parser.add_argument("--todos", action="store_true", help="reimprime todos los mensajes")
    args = parser.parse_args()

    mensajes = servidor.leer_archivo()
    if not mensajes:
        print(f"El archivo esta vacio o no existe: {servidor.ARCHIVO_PATH}")
        return

    if args.todos:
        elegidos = list(range(1, len(mensajes) + 1))
    elif args.ultimos:
        elegidos = list(range(max(1, len(mensajes) - args.ultimos + 1), len(mensajes) + 1))
    elif args.numeros:
        fuera = [n for n in args.numeros if not 1 <= n <= len(mensajes)]
        if fuera:
            sys.exit(f"Numeros fuera de rango (hay {len(mensajes)} mensajes): {fuera}")
        elegidos = args.numeros
    else:
        listar(mensajes)
        return

    # Confirmar antes de gastar mucho papel.
    if len(elegidos) > 3:
        respuesta = input(f"Se van a imprimir {len(elegidos)} recibos. ¿Seguir? [s/N] ")
        if respuesta.strip().lower() != "s":
            print("Cancelado.")
            return

    for numero in elegidos:
        mensaje = mensajes[numero - 1]
        try:
            impresora.imprimir_imagen(servidor.renderizar_texto(mensaje["texto"]))
        except impresora.ErrorImpresora as e:
            sys.exit(f"Error al imprimir el mensaje {numero}: {e}")
        print(f"Reimpreso {numero}: {mensaje['texto'][:LARGO_VISTA_PREVIA]!r}")


if __name__ == "__main__":
    main()
