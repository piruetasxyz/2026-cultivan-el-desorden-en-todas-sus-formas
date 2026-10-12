# 2026-cultivan-el-desorden-en-todas-sus-formas

Instalación de mensajes impresos: las personas escanean un QR con su teléfono, abren una página con una caja de texto, escriben un mensaje (máximo 250 caracteres) y se imprime en una impresora térmica de tickets, en la tipografía [Space Mono](https://fonts.google.com/specimen/Space+Mono). Cada mensaje queda guardado en un archivo, para reimprimirlo o exportarlo a PDF.

Todos los recibos miden lo mismo (aprox. 6 cm): el alto alcanza para un mensaje de 250 caracteres. Si un mensaje no cabe (por ejemplo, con muchos saltos de línea), la letra se achica; si aun así no cabe, se cortan las líneas que sobran.

Una primera prueba de concepto (captura e impresión de bibliotecacuir.org) quedó en el historial de git, en la carpeta `antiguo/` del commit `965a721`.

## Hardware

- Impresora térmica ESC/POS **TX-30 II** (clon genérico, "printer-80"), conectada por USB.
  - `idVendor = 0x0483`, `idProduct = 0x5743`
  - Configurada para rollo de 80 mm (576 dots de ancho, 8 dots por mm).
- Rollo de papel térmico de **58 mm** (384 dots de ancho útil).
- Un computador macOS (probado en Mac con Apple Silicon).
- Una red Wi-Fi a la que se conectan el computador y los teléfonos.

## Archivos

| Archivo | Qué hace |
| --- | --- |
| [codigo/servidor.py](codigo/servidor.py) | Servidor web en el puerto **5050**, accesible desde la red local. Al iniciar imprime el QR. |
| [codigo/impresora.py](codigo/impresora.py) | Envía imágenes a la impresora por USB, con el margen para rollo de 58 mm. |
| [codigo/reimprimir.py](codigo/reimprimir.py) | Lista y reimprime mensajes del archivo. |
| [codigo/exportar_pdf.py](codigo/exportar_pdf.py) | Exporta mensajes del archivo a PDF, con el mismo aspecto que los recibos. |
| [codigo/calibrar_ancho.py](codigo/calibrar_ancho.py) | Imprime una regla a lo ancho de todo el cabezal para calibrar el margen. |
| [codigo/requirements.txt](codigo/requirements.txt) | Dependencias de Python. |
| [fuentes/SpaceMono/](fuentes/SpaceMono/) | Tipografía Space Mono (licencia SIL Open Font License, ver `OFL.txt`). Se usa en los recibos, el PDF y la página web. |

## Instalación (una sola vez)

1. Instalar [Homebrew](https://brew.sh) si no está instalado, y luego `libusb` y Python:

   ```sh
   brew install libusb python@3.12
   ```

2. Desde la raíz de este repositorio, crear un entorno virtual e instalar las dependencias:

   ```sh
   python3.12 -m venv .venv
   .venv/bin/pip install -r codigo/requirements.txt
   ```

## Uso

1. Conectar la impresora por USB y encenderla, y conectar el computador a la red Wi-Fi.
2. Levantar el servidor:

   ```sh
   .venv/bin/python codigo/servidor.py
   ```

   Se imprime un ticket con el QR y la dirección (por ejemplo `http://10.20.14.80:5050`). Para no imprimir el QR: agregar `--sin-qr`.

3. Escanear el QR con un teléfono **conectado a la misma red Wi-Fi**, escribir un mensaje y apretar "Imprimir". Al imprimirse, la caja de texto se vacía. Si algo falla (límite por hora, impresora apagada, conexión), aparece un aviso bajo el botón.
4. Para detener el servidor: `Ctrl + C` en la terminal.

## Archivo, reimpresión y PDF

Cada mensaje impreso se guarda en `archivo/mensajes.jsonl` (una línea por mensaje, con fecha y texto). No se guarda la IP ni ningún dato del teléfono. La carpeta `archivo/` está en `.gitignore`: los mensajes del público no se suben al repositorio. Conviene respaldarla aparte.

Reimprimir:

```sh
.venv/bin/python codigo/reimprimir.py                # lista todos los mensajes, numerados
.venv/bin/python codigo/reimprimir.py 3 7 12         # reimprime los mensajes 3, 7 y 12
.venv/bin/python codigo/reimprimir.py --ultimos 5    # reimprime los últimos 5
.venv/bin/python codigo/reimprimir.py --todos        # reimprime todos
```

Antes de imprimir más de 3 recibos pide confirmación. Se puede reimprimir con el servidor funcionando, pero si justo coincide con una impresión del público la impresora puede responder "Access denied": basta con esperar y volver a correrlo.

Exportar a PDF (una página por recibo, de 48 × 61 mm, con la misma tipografía y los mismos cortes de línea que el papel; el texto queda vectorial, así que se puede buscar y copiar):

```sh
.venv/bin/python codigo/exportar_pdf.py                  # todos → archivo/mensajes.pdf
.venv/bin/python codigo/exportar_pdf.py 3 7 12           # solo esos números
.venv/bin/python codigo/exportar_pdf.py --ultimos 10     # los últimos 10
.venv/bin/python codigo/exportar_pdf.py --salida otro.pdf
```

## Límites

- Máximo 250 caracteres por mensaje (`LARGO_MAXIMO` en [codigo/servidor.py](codigo/servidor.py)). Al cambiarlo, el largo de todos los recibos se ajusta solo.
- Máximo 5 mensajes por teléfono por hora (`MENSAJES_POR_VENTANA` y `VENTANA_SEGUNDOS` en [codigo/servidor.py](codigo/servidor.py)). Cada teléfono se identifica por su IP en la red local. Los contadores se reinician al reiniciar el servidor. Si la IP de un teléfono cambia (por ejemplo, al desconectarse y volver a conectarse al Wi-Fi), empieza con el cupo completo.

## Margen para rollo de 58 mm

La impresora está configurada para 80 mm. Con un rollo de 58 mm el papel no cubre todo el cabezal, así que el contenido se corre hacia donde está el papel con un margen blanco a la izquierda (`MARGEN_IZQUIERDO_PX` en [codigo/impresora.py](codigo/impresora.py), actualmente **64 dots = 8 mm**).

Además, la impresora corre hacia la derecha las imágenes más angostas que el cabezal. Por eso siempre se envían imágenes de 576 dots de ancho, con el contenido a `MARGEN_IZQUIERDO_PX` del borde.

Para recalibrar (por ejemplo, con otra impresora u otro rollo):

1. Imprimir la regla (también sirve para probar que la conexión USB funciona):

   ```sh
   .venv/bin/python codigo/calibrar_ancho.py
   ```

2. Anotar el número más pequeño y el más grande que se leen en el papel.
3. Elegir un margen que deje el recibo (384 dots) centrado entre esos dos valores, y cambiar `MARGEN_IZQUIERDO_PX`. También se puede probar sin editar el código:

   ```sh
   MARGEN_IZQUIERDO_PX=56 .venv/bin/python codigo/servidor.py --sin-qr
   ```

Cada dot es 1/8 de mm: para mover el contenido 2 mm a la izquierda, restar 16 al margen.

Con un rollo de 80 mm: `ANCHO_PAPEL_PX=576 MARGEN_IZQUIERDO_PX=0 .venv/bin/python codigo/servidor.py`.

## Red

- La dirección IP del computador puede cambiar al cambiar de red o al reiniciar el router. Si cambia, hay que volver a imprimir el QR (reiniciar el servidor). Con un router propio conviene reservar una IP fija para el computador ("reserva DHCP"), así el QR impreso sirve siempre.
- En una red sin internet (hotspot del Mac, router sin conexión, Raspberry Pi) la detección automática de la IP puede fallar y el QR saldría con `127.0.0.1`. En ese caso, indicar la IP a mano: `IP_SERVIDOR=192.168.2.1 .venv/bin/python codigo/servidor.py`.
- La primera vez, macOS puede preguntar si se permiten conexiones entrantes para Python: hay que aceptar.
- Algunas redes (universidades, cafés, eventos) aíslan a los dispositivos entre sí y el teléfono no puede llegar al computador. En ese caso, usar un router propio o el hotspot del teléfono.
- Los teléfonos a veces se desconectan solos de una red Wi-Fi y pasan a datos móviles; si la página no carga, revisar que el teléfono siga en la misma red.

## Problemas comunes

- **"No se encontró la impresora USB"**: revisar cable, que esté encendida, y que los IDs coincidan. Para ver los dispositivos USB conectados: `system_profiler SPUSBDataType`.
- **"Error de USB (posible problema de permisos)" / "Access denied"**: cerrar cualquier otro programa que esté usando la impresora (incluido otro servidor abierto) y reconectar el cable. Si la impresora fue agregada en *Ajustes del Sistema → Impresoras*, quitarla de ahí: este proyecto le habla directo por USB, sin CUPS.
- **Sale el papel cortado pero en blanco**: el rollo está al revés. El papel térmico solo se marca por un lado; al rasparlo con la uña, el lado que se oscurece debe mirar hacia el cabezal.
- **La impresión sale corrida, cortada o con mucho blanco a un lado**: recalibrar el margen (ver "Margen para rollo de 58 mm"). Si la impresora se usó con otro programa, apagarla y encenderla borra la configuración que haya quedado guardada.
- **Los emojis no se ven**: Space Mono no los incluye. Acentos, ñ, ¿ y ¡ sí funcionan, porque el texto se imprime como imagen.

## Pendientes

Notas para las próximas iteraciones. Todavía no están probadas.

### 1. Rollo ancho de 80 mm

El rollo que compró la clienta o el cliente probablemente es de 80 mm. Para confirmarlo, medir el ancho del papel con una regla: un rollo de 80 mm mide aprox. 79–80 mm, y uno de 58 mm aprox. 57–58 mm.

La impresora ya está configurada para 80 mm (576 dots), así que en principio basta con decirle al código que el papel cubre todo el cabezal:

```sh
ANCHO_PAPEL_PX=576 MARGEN_IZQUIERDO_PX=0 .venv/bin/python codigo/servidor.py
```

Qué revisar:

- [ ] Si dentro de la impresora hay un separador o guía para rollo angosto, quitarlo antes de poner el rollo de 80 mm.
- [ ] Imprimir la regla (`.venv/bin/python codigo/calibrar_ancho.py`): con el rollo de 80 mm deberían verse todos los números, de `0` a `528`. Si no, ajustar `MARGEN_IZQUIERDO_PX` y quizás bajar un poco `ANCHO_PAPEL_PX`.
- [ ] Con el papel más ancho caben más caracteres por línea, así que el alto fijo de los recibos se recalcula solo y los recibos salen más cortos y anchos. Si se quiere mantener la proporción, subir `TAMANO_TEXTO` en [codigo/servidor.py](codigo/servidor.py) (por ejemplo, de 26 a 36).
- [ ] El QR y el PDF se adaptan solos al nuevo ancho (el PDF pasaría a 72 mm de ancho); revisar que se vean bien.
- [ ] Una vez decidido, dejar el ancho y el margen de 80 mm como valores por defecto en [codigo/impresora.py](codigo/impresora.py), o agregar una sola opción (por ejemplo `ROLLO=80mm`) que cambie ambos.

### 2. Raspberry Pi 4 o 5

La idea: que una Raspberry Pi haga todo sola, sin el Mac: crear la red Wi-Fi, correr el servidor e imprimir. Se enchufa y la obra queda funcionando. Sirven tanto la Pi 4 como la Pi 5; para esto la Pi 4 alcanza de sobra.

El código ya es portable: no usa tipografías ni rutas de macOS (Space Mono viene en el repo).

**Instalación** (Raspberry Pi OS de 64 bits, versión Bookworm o más nueva):

```sh
sudo apt update
sudo apt install -y git python3-venv libusb-1.0-0
git clone <url-de-este-repo>
cd 2026-cultivan-el-desorden-en-todas-sus-formas
python3 -m venv .venv
.venv/bin/pip install -r codigo/requirements.txt
```

**Permisos USB.** En Linux un usuario normal no puede hablarle a la impresora sin una regla de udev:

```sh
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5743", MODE="0666"' | sudo tee /etc/udev/rules.d/99-impresora-termica.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Desconectar y volver a conectar la impresora. Si al imprimir aparece "Resource busy", es el driver de impresoras de Linux (`usblp`) que se adueña del USB: desactivarlo con `echo "blacklist usblp" | sudo tee /etc/modprobe.d/sin-usblp.conf` y reiniciar.

**Red Wi-Fi propia.** La Pi puede crear su propia red, y siempre toma la IP `10.42.0.1`, así que el QR impreso sirve para siempre:

```sh
sudo nmcli device wifi hotspot ifname wlan0 ssid "cultivan" password "una-clave-larga"
sudo nmcli connection modify Hotspot connection.autoconnect yes
```

Pendiente decidir si la red va abierta (sin clave, más fácil para el público) o con clave (impresa junto al QR). También se podría imprimir un segundo QR que conecte el teléfono a la red directamente.

**Arranque automático.** Crear `/etc/systemd/system/cultivan.service`, cambiando `USUARIO` por el usuario de la Pi:

```ini
[Unit]
Description=Cultivan el desorden: servidor de mensajes
After=network-online.target

[Service]
User=USUARIO
WorkingDirectory=/home/USUARIO/2026-cultivan-el-desorden-en-todas-sus-formas
Environment=IP_SERVIDOR=10.42.0.1
ExecStart=/home/USUARIO/2026-cultivan-el-desorden-en-todas-sus-formas/.venv/bin/python codigo/servidor.py --sin-qr
Restart=always

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl enable --now cultivan
journalctl -u cultivan -f    # ver el log en vivo
```

Lleva `--sin-qr` porque, con la IP fija, el QR se imprime una sola vez y no hace falta gastar papel en cada encendido.

**Diferencias entre Pi 4 y Pi 5:**

| | Pi 4 | Pi 5 |
| --- | --- | --- |
| Fuente de poder | USB-C 5 V / 3 A (oficial de 15 W) | USB-C 5 V / 5 A (oficial de 27 W) |
| Botón de encendido | No: apagar con `sudo shutdown now` antes de desenchufar | Sí: un toque lo apaga de forma segura |
| Reloj sin internet | Pierde la hora al apagarse; las fechas del archivo pueden quedar mal | Tiene reloj propio si se le conecta la batería oficial de RTC |

La impresora usa su propia fuente de poder, no la de la Pi.

**Otras cosas a tener en cuenta:**

- [ ] **La hora.** Sin internet, la Pi no sabe la hora y las fechas de `archivo/mensajes.jsonl` saldrían mal. En la Pi 5, conectar la batería de RTC. En la Pi 4, se puede agregar un módulo RTC, o aceptar que el orden de los mensajes es correcto aunque la fecha no.
- [ ] **No desenchufar en caliente.** Cortar la luz sin apagar puede dañar la tarjeta SD, y el archivo vive ahí. Respaldar `archivo/` seguido (por ejemplo, copiándolo a un pendrive o al Mac con `scp`).
- [ ] **Desarrollar desde el Mac.** Editar en el Mac, hacer push, y en la Pi hacer `git pull` y `sudo systemctl restart cultivan`. Para entrar a la Pi: `ssh USUARIO@<nombre-de-la-pi>.local`.
- [ ] **Avisos de "sin internet".** Los teléfonos avisan que la red no tiene internet y algunos Android se cambian solos a datos móviles; hay que tocar "mantener conexión". Un portal cautivo (que abra la página sola al conectarse) lo resolvería, pero es más trabajo.
