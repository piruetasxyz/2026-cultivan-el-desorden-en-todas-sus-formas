#!/usr/bin/env python3
"""
Prueba de impresion directa por USB (ESC/POS) sin pasar por CUPS.
Impresora: TX-30 II (clon generico), idVendor=0x0483, idProduct=0x5743
"""

from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError
import usb.core
import sys

VENDOR_ID = 0x0483
PRODUCT_ID = 0x5743

def main():
    print(f"Buscando dispositivo USB {VENDOR_ID:#06x}:{PRODUCT_ID:#06x} ...")

    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        print("ERROR: No se encontro ningun dispositivo USB con esos IDs.")
        print("Verifica que la impresora este conectada y encendida.")
        sys.exit(1)

    print(f"Dispositivo encontrado: {device}")

    try:
        printer = Usb(VENDOR_ID, PRODUCT_ID)
        print("Conexion establecida con la impresora.")

        # ESC @: reinicia la configuracion guardada en la impresora.
        printer.hw("INIT")

        # Lineas cortas con espacios al inicio para que caigan sobre un
        # rollo de 58mm (la impresora esta configurada para 80mm).
        margen = " " * 6

        printer.text(margen + "== Prueba ESC/POS ==\n")
        printer.text(margen + "USB directo, sin CUPS.\n")
        printer.text(margen + "Si ves esto, funciona.\n")
        printer.text("\n")

        printer.cut()
        print("Comando de corte enviado. Prueba completada con exito.")

    except USBNotFoundError as e:
        print(f"ERROR: No se pudo abrir el dispositivo USB: {e}")
        sys.exit(1)
    except usb.core.USBError as e:
        print(f"ERROR de USB (posible problema de permisos): {e}")
        print("Revisa el diagnostico de permisos USB en macOS.")
        sys.exit(1)

if __name__ == "__main__":
    main()
