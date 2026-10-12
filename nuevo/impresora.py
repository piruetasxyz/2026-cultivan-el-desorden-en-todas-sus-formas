#!/usr/bin/env python3
"""
Funciones para imprimir imagenes en la impresora termica ESC/POS
(TX-30 II / printer-80) por USB, con rollo angosto de 58mm.
"""

from __future__ import annotations

import os

from PIL import Image
from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError
import usb.core

ID_VENDOR = 0x0483
ID_PRODUCTO = 0x5743

# La impresora esta configurada para 80mm (576 dots) y el rollo es de 58mm.
# Calibrado con antiguo/calibrar_ancho.py: el papel cubre aprox. de 48 a
# 462 dots, asi que con 64 de margen la imagen de 384 px queda centrada.
ANCHO_CABEZAL_PX = 576
ANCHO_PAPEL_PX = int(os.environ.get("ANCHO_PAPEL_PX", "384"))
MARGEN_IZQUIERDO_PX = int(os.environ.get("MARGEN_IZQUIERDO_PX", "64"))


class ErrorImpresora(Exception):
    """Error al comunicarse con la impresora USB."""


def agregar_margen(imagen: Image.Image, margen_px: int = MARGEN_IZQUIERDO_PX) -> Image.Image:
    """Pega la imagen a `margen_px` del borde izquierdo de un lienzo blanco
    del ancho completo del cabezal. Siempre se envia el ancho completo
    porque la impresora no alinea a la izquierda las imagenes mas angostas
    (las corre hacia la derecha), igual que la regla de calibracion."""
    con_margen = Image.new("RGB", (ANCHO_CABEZAL_PX, imagen.height), "white")
    con_margen.paste(imagen.convert("RGB"), (margen_px, 0))
    return con_margen


def imprimir_imagen(imagen: Image.Image) -> None:
    if usb.core.find(idVendor=ID_VENDOR, idProduct=ID_PRODUCTO) is None:
        raise ErrorImpresora(
            "No se encontro la impresora USB. Revisa que este conectada y encendida."
        )
    impresora = None
    try:
        impresora = Usb(ID_VENDOR, ID_PRODUCTO, profile="default")
        # ESC @: reinicia la configuracion de la impresora. Los margenes y
        # anchos de area (GS L / GS W) quedan guardados hasta apagarla, y
        # se sumarian al margen que agregamos a la imagen.
        impresora.hw("INIT")
        impresora.image(agregar_margen(imagen))
        impresora.text("\n")
        impresora.cut()
    except USBNotFoundError as e:
        raise ErrorImpresora(f"No se pudo abrir el dispositivo USB: {e}") from e
    except usb.core.USBError as e:
        raise ErrorImpresora(f"Error de USB (posible problema de permisos): {e}") from e
    finally:
        # Liberar el USB: si el servidor lo deja reclamado, la siguiente
        # impresion falla con "Access denied".
        if impresora is not None:
            impresora.close()
