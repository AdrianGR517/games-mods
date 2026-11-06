# Mod Classic Controller para Metroid Prime Trilogy (pre1.0)

Código Gecko para jugar a **Metroid Prime Trilogy** (Wii, PAL **R3MP01**) con el **mando clásico**: Metroid Prime,
Metroid Prime 2: Echoes, Metroid Prime 3: Corruption y el menú de Trilogy, todo en un solo código.

**Estado:** probado en Dolphin; las pruebas en una Wii real (USB Loader GX) están en curso.

## Archivos
| Archivo | Uso |
|---|---|
| `codes/R3MP01.ini` | El código, ya activado, para Dolphin |
| `codes/R3MP01.gct` | El código, para la Wii |
| `codes/R3MP01.txt` | El código en texto, para el gestor de trucos de USB Loader GX |
| `codes/classic_controller.txt` | El código solo, para pegarlo a mano |

## Instalar en Dolphin
1. Activa los trucos: *Configuración → General → Habilitar trucos*.
2. Copia `R3MP01.ini` en `Documentos\Dolphin Emulator\GameSettings\` (guarda antes el tuyo si ya tenías uno).
3. Pon el Wiimote 1 como *Wiimote emulado* con el **Mando Clásico** como extensión.
4. En *Propiedades → Códigos Gecko* del juego, activa **solo** «Classic Controller pre1.0».

## Instalar en la Wii (USB Loader GX)
1. Copia `R3MP01.gct` a `SD:/codes/R3MP01.gct` (quita antes cualquier otro R3MP01.gct que haya ahí).
2. En USB Loader GX, ajustes del juego (Trilogy):
   - **Ocarina: Sí.**
   - **Tipo de gancho (Hook Type): VBI** (el que viene por defecto). Si los controles no hacen nada, prueba AXNextFrame.
   - **Depurador / Gecko debugger: No.** Con el depurador activado solo caben 1864 B de códigos y el mod no cargaría.
   - **DOL alternativo: No.** Arranca Trilogy normal y elige el juego en su menú: el cargador vuelve a enganchar los
     códigos cada vez que el menú arranca uno de los juegos.
3. Conecta el mando clásico al Wiimote antes de arrancar el juego. **No toques los sticks mientras arranca:** la Wii
   toma esa posición como el centro.
4. Si el cargador dice que no encuentra el archivo de trucos: copia `R3MP01.txt` a `SD:/txtcodes/`, abre el gestor
   de trucos del juego en USB Loader GX, marca «Classic Controller pre1.0» y crea el GCT desde ahí (sale igual que
   `R3MP01.gct`).

## Controles
**Menús** (pausa, inventario, menú de Trilogy, menú HOME de la Wii y menús del juego)
| Clásico | Acción |
|---|---|
| Stick izquierdo | Puntero (con aceleración; se queda quieto al soltar) |
| Stick derecho | Nada |
| A | Aceptar |
| B | Atrás |
| R / ZL | Nada |
| Cruceta | Cruceta |
| − / + | Lo mismo que al jugar (sirven para cerrar el mapa o la pausa) |
| HOME | Abrir y cerrar el menú HOME |

**Pausa de MP1** (la que abre el +): igual que los menús, y además
| Clásico | Acción |
|---|---|
| Cruceta izquierda | Opciones (el − del Wiimote) |
| Cruceta derecha | Banco de datos (el + del Wiimote) |
| Cruceta izquierda / derecha en el aviso de salir de la partida | Izquierda / derecha (para elegir) |

**Mapa de MP1 y MP2** (el que abre el −): igual que los menús, y además
| Clásico | Acción |
|---|---|
| Cruceta arriba / abajo | Zoom + / zoom − (mantener) |
| Stick izquierdo | Girar el mapa (y mover el puntero), como antes |
| L + stick izquierdo | Mover el mapa |
| Y | Leyenda (la C del Nunchuk) |

**Mapa de MP3**
| Clásico | Acción |
|---|---|
| Stick izquierdo | Solo el puntero |
| Stick derecho | Girar el mapa |
| L + stick derecho | Desplazar el mapa |
| Cruceta arriba / abajo | Zoom + / zoom − |
| Y | La C del Nunchuk (lo mismo que en MP1/MP2) |

**Pausa de MP2**: igual que el mapa (zoom con la cruceta, Y = leyenda (C), L + stick izquierdo = mover).

**Jugando** (MP1, MP2 y MP3)
| Clásico | Acción |
|---|---|
| Stick izquierdo | Moverse |
| Stick derecho | Cámara, con la mira siempre en el centro · en las ruletas: elegir opción (tras 0,7 s sin tocarlo vuelve al centro) |
| Stick izquierdo en las secciones con la mano (MP3) | Mover la mano; el stick derecho sigue con la cámara |
| A / R | Disparar (mantener = cargar) |
| ZR | Misil |
| L | Fijar blanco |
| B / ZL | Saltar |
| Y | Morfosfera |
| Cruceta arriba (mantener) | Ruleta de visores |
| Cruceta abajo (mantener) | MP1 y MP2: ruleta de rayos · MP3: pista (el 2 del Wiimote) |
| Cruceta izquierda / derecha | MP1 y MP2: rayo anterior / siguiente, saltando los que no tienes · MP3: nada |
| − | MP1 y MP2: mapa · MP3: pausa |
| + | MP1 y MP2: pausa · MP3: hipermodo · mantener 1 s en una cinemática: saltarla |
| HOME | Menú HOME (y cerrarlo) |

**MP3: controles de movimiento**
| Clásico | Acción |
|---|---|
| L + X (con un punto de gancho o un blanco de látigo fijado) | Lanzar el gancho o el látigo |
| Stick izquierdo abajo (con el látigo enganchado) | Tirar (Samus no anda hacia atrás); si lo mantienes, arranca lo enganchado |
| X (mantener) | Agitar: quitarse de encima a los enemigos que se enganchan |
| Stick izquierdo a los lados | Girar cerraduras de combinación y escáneres de ADN |
| A + stick izquierdo | Palancas, asas y células: agarrar con A; meter = stick adelante, sacar = atrás, girar = a los lados (al revés, retrocede) |

**Morfosfera** (los tres juegos) – sin cambios
| Clásico | Acción |
|---|---|
| A / R | Bomba |
| X | Salto (bola muelle): una sola sacudida por pulsación |
| B / ZL | Impulso (mantener y soltar) |
| L | Aracnosfera |
| ZR | Bomba de energía |
| Y | Salir de la morfosfera |

**Cinemáticas:** mantener **+ 1 segundo** las salta en los tres juegos.

## Problemas conocidos
- **La mano de MP3 rebota un poco** al llevarla a tope a un lado de una consola.
- **Los iconos del juego siguen siendo los del Wiimote y el Nunchuk.**
- **Stick «atascado» al arrancar:** suelta los sticks y vuelve a conectar el mando.
- **No caben otros códigos grandes:** el mod ocupa 2984 de los 3272 B que admite Dolphin.

## Cómo está hecho
El mod completo ocupa 4144 B, más de lo que cabe, así que el código va **comprimido** (2984 B) y se descomprime solo
en memoria libre al arrancar. La lógica de los controles se escribe una vez y la comparten los tres juegos; cada juego
solo aporta sus direcciones. Para regenerarlo: `pip install keystone-engine` y `python src/base.py out`.
