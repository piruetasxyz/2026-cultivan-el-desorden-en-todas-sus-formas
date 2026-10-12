# 2026-cultivan-el-desorden-en-todas-sus-formas

Instalación que captura el sitio [bibliotecacuir.org](https://bibliotecacuir.org/) en formato móvil (o su código fuente) y lo imprime en una impresora térmica de tickets por USB. Se controla desde una interfaz web local con botones.

El código original está en la carpeta [antiguo/](antiguo/). La nueva versión, en desarrollo, está en [nuevo/](nuevo/).

## Hardware

- Impresora térmica ESC/POS **TX-30 II** (clon genérico, "printer-80"), conectada por USB.
  - `idVendor = 0x0483`, `idProduct = 0x5743`
- Rollo de papel de **80 mm** (ancho, 576 px) o **58 mm** (angosto, 384 px).
- Un computador macOS (probado en Mac con Apple Silicon).

## Archivos

| Archivo | Qué hace |
| --- | --- |
| [antiguo/print_server.py](antiguo/print_server.py) | Servidor web (Flask) con la interfaz de botones en `http://127.0.0.1:5005`. **Es el que se usa en la exhibición.** |
| [antiguo/printer_lib.py](antiguo/printer_lib.py) | Funciones de captura, recorte, encabezado e impresión. Aquí se cambian URL, tamaños, tipografías, etc. |
| [antiguo/test_printer.py](antiguo/test_printer.py) | Prueba mínima: imprime un texto y corta el papel. Sirve para verificar la conexión USB. |
| [antiguo/calibrar_ancho.py](antiguo/calibrar_ancho.py) | Imprime una regla a lo ancho de todo el cabezal para calibrar el margen con un rollo angosto. |
| [antiguo/print_webpage.py](antiguo/print_webpage.py) | Versión antigua de línea de comandos (captura e imprime una vez). |
| [antiguo/requirements.txt](antiguo/requirements.txt) | Dependencias de Python. |

## Instalación (una sola vez)

1. Instalar [Homebrew](https://brew.sh) si no está instalado, y luego `libusb` y Python:

   ```sh
   brew install libusb python@3.12
   ```

2. Desde la raíz de este repositorio, crear un entorno virtual e instalar las dependencias:

   ```sh
   python3.12 -m venv .venv
   .venv/bin/pip install -r antiguo/requirements.txt
   .venv/bin/playwright install chromium
   ```

3. (Opcional) Instalar la tipografía [Montserrat](https://fonts.google.com/specimen/Montserrat) en `~/Library/Fonts/Montserrat[wght].ttf` para el encabezado. Si no está, se usa Helvetica Bold.

4. (Opcional) Para imprimir el código fuente desde una copia local del sitio, clonar el repositorio en `antiguo/bibliotecacuir.github.io/`, o indicar otra ruta con la variable de entorno `REPO_ROOT`. Si no hay copia local, el archivo se descarga en vivo desde bibliotecacuir.org.

## Uso

1. Conectar la impresora por USB y encenderla.
2. Probar la conexión:

   ```sh
   .venv/bin/python antiguo/test_printer.py
   ```

   Debería imprimir "Prueba de impresora ESC/POS" y cortar el papel.

3. Levantar el servidor:

   ```sh
   .venv/bin/python antiguo/print_server.py
   ```

4. Abrir [http://127.0.0.1:5005](http://127.0.0.1:5005) en el navegador. Desde ahí se elige:
   - **Ancho de rollo**: 80 mm o 58 mm (tiene que coincidir con el papel puesto).
   - **Qué imprimir**: el sitio web o su código fuente (`index.html`).
   - **Cantidad de copias**: 1, 2, 5 o 10. Cada copia es una captura nueva: cambia la foto principal y la fase del carrusel ovalado.
   - **Formato LARGO**: imprime el scroll completo de la página.
   - **Formato CORTO**: imprime solo los primeros N centímetros.

5. Para detener el servidor: `Ctrl + C` en la terminal.

La interfaz solo es accesible desde el mismo computador (`127.0.0.1`), no desde otros dispositivos de la red.

## Rollo angosto (58 mm) en impresora configurada para 80 mm

La impresora está configurada para 80 mm y empieza a imprimir en el borde izquierdo del cabezal. Con un rollo de 58 mm, el papel no cubre ese borde y la impresión sale cortada a la izquierda. Para compensarlo, se agrega un margen blanco a la izquierda (`MARGEN_IZQUIERDO_PX` en [antiguo/printer_lib.py](antiguo/printer_lib.py), actualmente **64 dots = 8 mm**).

Para recalibrar (por ejemplo, con otra impresora u otro rollo):

1. Imprimir la regla:

   ```sh
   .venv/bin/python antiguo/calibrar_ancho.py
   ```

2. Anotar el número más pequeño y el más grande que se leen en el papel.
3. Elegir un margen que deje la imagen (384 px para 58 mm) centrada entre esos dos valores, y cambiar `MARGEN_IZQUIERDO_PX`. También se puede probar sin editar el código:

   ```sh
   MARGEN_IZQUIERDO_PX=80 .venv/bin/python antiguo/print_server.py
   ```

Con rollo de 80 mm, usar `MARGEN_IZQUIERDO_PX=0` y elegir "80mm" en la interfaz.

## Modificar

Los parámetros principales están al inicio de [antiguo/printer_lib.py](antiguo/printer_lib.py):

- `URL`: sitio a capturar.
- `HEADER_TEXT`: texto del encabezado impreso arriba de cada captura.
- `MOBILE_WIDTH`, `MOBILE_HEIGHT`: tamaño del viewport del "teléfono" simulado.
- `ROLL_PRESETS_PX`: ancho de impresión en píxeles según el rollo.
- `HOME_SLIDE_COUNT`: cantidad de imágenes del hero de bibliotecacuir.org entre las que se elige una al azar. Esto es específico de ese sitio. Si se cambia la `URL`, probablemente haya que quitar o adaptar esa parte de `capture_full_page`.

## Problemas comunes

- **"No se encontró la impresora USB"**: revisar cable, que esté encendida, y que los IDs coincidan. Para ver los dispositivos USB conectados: `system_profiler SPUSBDataType`.
- **"Error de USB (posible problema de permisos)" / "Access denied"**: cerrar cualquier otro programa que esté usando la impresora (incluido otro `print_server.py` abierto) y reconectar el cable. Si la impresora fue agregada en *Ajustes del Sistema → Impresoras*, quitarla de ahí: este proyecto le habla directo por USB, sin CUPS.
- **Sale el papel cortado pero en blanco**: el rollo está al revés. El papel térmico solo se marca por un lado; al rasparlo con la uña, el lado que se oscurece debe mirar hacia el cabezal.
- **La impresión sale cortada o con márgenes raros**: verificar que el ancho de rollo elegido en la interfaz coincida con el papel puesto, y recalibrar el margen (ver sección de rollo angosto).
- **Error de Playwright / Chromium**: volver a correr `.venv/bin/playwright install chromium`.

## nuevo: mensajes desde el teléfono

Las personas escanean un QR impreso con su teléfono, abren una página con una caja de texto, escriben un mensaje (máximo 250 caracteres) y se imprime en la impresora térmica, en la tipografía [Space Mono](https://fonts.google.com/specimen/Space+Mono).

Todos los recibos miden lo mismo (aprox. 6 cm): el alto alcanza para un mensaje de 250 caracteres. Si un mensaje no cabe (por ejemplo, con muchos saltos de línea), la letra se achica; si aun así no cabe, se cortan las líneas que sobran.

| Archivo | Qué hace |
| --- | --- |
| [nuevo/servidor.py](nuevo/servidor.py) | Servidor web en el puerto **5050**, accesible desde la red local. Al iniciar imprime el QR. |
| [nuevo/reimprimir.py](nuevo/reimprimir.py) | Lista y reimprime mensajes del archivo. |
| [nuevo/exportar_pdf.py](nuevo/exportar_pdf.py) | Exporta mensajes del archivo a PDF, con el mismo aspecto que los recibos. |
| [nuevo/impresora.py](nuevo/impresora.py) | Envía imágenes a la impresora por USB, con el margen para rollo de 58 mm. |
| [nuevo/requirements.txt](nuevo/requirements.txt) | Dependencias de Python. |
| [fuentes/SpaceMono/](fuentes/SpaceMono/) | Tipografía Space Mono (licencia SIL Open Font License, ver `OFL.txt`). Se usa en los recibos y en la página web. |

### Instalación

Con el entorno virtual de la sección anterior ya creado:

```sh
.venv/bin/pip install -r nuevo/requirements.txt
```

### Uso

1. Conectar la impresora por USB y el computador a la red Wi-Fi.
2. Levantar el servidor:

   ```sh
   .venv/bin/python nuevo/servidor.py
   ```

   Se imprime un ticket con el QR y la dirección (por ejemplo `http://10.20.14.80:5050`). Para no imprimir el QR: agregar `--sin-qr`.

3. Escanear el QR con un teléfono **conectado a la misma red Wi-Fi**, escribir un mensaje y apretar "Imprimir".
4. Para detener el servidor: `Ctrl + C` en la terminal.

### Archivo y reimpresión

Cada mensaje impreso se guarda en `archivo/mensajes.jsonl` (una línea por mensaje, con fecha y texto). No se guarda la IP ni ningún dato del teléfono. La carpeta `archivo/` está en `.gitignore`: los mensajes del público no se suben al repositorio. Conviene respaldarla aparte.

```sh
.venv/bin/python nuevo/reimprimir.py                # lista todos los mensajes, numerados
.venv/bin/python nuevo/reimprimir.py 3 7 12         # reimprime los mensajes 3, 7 y 12
.venv/bin/python nuevo/reimprimir.py --ultimos 5    # reimprime los últimos 5
.venv/bin/python nuevo/reimprimir.py --todos        # reimprime todos
```

Para exportar a PDF (una página por recibo, de 48 × 61 mm, con la misma tipografía y los mismos cortes de línea que el papel; el texto queda vectorial, así que se puede buscar y copiar):

```sh
.venv/bin/python nuevo/exportar_pdf.py                  # todos → archivo/mensajes.pdf
.venv/bin/python nuevo/exportar_pdf.py 3 7 12           # solo esos números
.venv/bin/python nuevo/exportar_pdf.py --ultimos 10     # los últimos 10
.venv/bin/python nuevo/exportar_pdf.py --salida otro.pdf
```

Antes de imprimir más de 3 recibos pide confirmación. Se puede reimprimir con el servidor funcionando, pero si justo coincide con una impresión del público la impresora puede responder "Access denied": basta con esperar y volver a correrlo.

### Notas

- La dirección IP del computador puede cambiar al cambiar de red o al reiniciar el router. Si cambia, hay que volver a imprimir el QR (reiniciar el servidor).
- En una red sin internet (hotspot del Mac, router sin conexión, Raspberry Pi) la detección automática de la IP puede fallar y el QR saldría con `127.0.0.1`. En ese caso, indicar la IP a mano: `IP_SERVIDOR=192.168.2.1 .venv/bin/python nuevo/servidor.py`.
- La impresora corre hacia la derecha las imágenes más angostas que el cabezal, por eso [nuevo/impresora.py](nuevo/impresora.py) siempre envía imágenes de 576 px de ancho con el contenido a `MARGEN_IZQUIERDO_PX` del borde.
- La primera vez, macOS puede preguntar si se permiten conexiones entrantes para Python: hay que aceptar.
- Algunas redes (universidades, cafés, eventos) aíslan a los dispositivos entre sí y el teléfono no puede llegar al computador. En ese caso, usar un router propio o el hotspot del teléfono.
- El texto se imprime como imagen, así que acentos y ñ funcionan. Los emojis no se ven.
- Máximo 5 mensajes por teléfono por hora (`MENSAJES_POR_VENTANA` y `VENTANA_SEGUNDOS` en [nuevo/servidor.py](nuevo/servidor.py)). Cada teléfono se identifica por su IP en la red local. Los contadores se reinician al reiniciar el servidor. Si la IP de un teléfono cambia (por ejemplo, al desconectarse y volver a conectarse al Wi-Fi), empieza con el cupo completo.
- Máximo 250 caracteres por mensaje (`LARGO_MAXIMO` en [nuevo/servidor.py](nuevo/servidor.py)). Al cambiarlo, el largo de todos los recibos se ajusta solo.
