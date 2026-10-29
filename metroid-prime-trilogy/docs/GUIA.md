# Mod Classic Controller para Metroid Prime Trilogy – pre1.0 (para probar en la Wii)

Disco: **R3MP01** (Trilogy PAL). Es la n0.10 tal cual (mismo código, 2984 de 3272 B), solo cambia el nombre.
En Dolphin salió bien todo lo probado (90 de 91; el rebote pequeño de la mano lo dejamos así).

## Comprobado para la Wii (USB Loader GX)
- **Sitio para los códigos:** USB Loader GX pone la lista en 0x800022A8 y admite hasta **3416 B**: el .gct (2984 B) cabe.
  (Dolphin admite 3272 B; también cabe.)
- **Su gestor de códigos:** he pasado las 269 pruebas del emulador con el gestor de USB Loader GX en vez del de Dolphin:
  **0 fallos**, y la memoria del juego queda idéntica a la de Dolphin. La prueba de «cargar un juego a mitad de
  descomprimir» también acaba igual que una carga limpia.
- **Cambiar de juego desde el menú de Trilogy:** USB Loader GX vuelve a enganchar los códigos cada vez que el menú
  arranca MP1, MP2 o MP3 (busca la misma secuencia en el .dol nuevo). He comprobado que los cuatro .dol del disco la
  tienen, y también el gancho «VBI». Así que se juega como en Dolphin: arrancas Trilogy y eliges el juego en su menú.

## Instalar en la Wii (USB Loader GX)
1. Copia `gct\R3MP01.gct` a `SD:/codes/R3MP01.gct` (quita antes cualquier otro R3MP01.gct que tengas ahí).
2. En USB Loader GX, ajustes del juego (Trilogy):
   - **Ocarina: Sí.**
   - **Tipo de gancho (Hook Type): VBI** (el que viene por defecto). Si los controles no hacen nada, prueba AXNextFrame.
   - **Depurador / Gecko debugger: No.** Con el depurador activado la lista va más arriba y solo caben 1864 B: el mod
     no cargaría.
   - **DOL alternativo: No.** Arranca Trilogy normal y elige el juego en su menú (el mod también lleva los controles
     del menú de Trilogy).
3. Conecta el mando clásico al Wiimote antes de arrancar el juego. **No toques los sticks mientras arranca:** la Wii
   toma esa posición como el centro.
4. Si el cargador dice que no encuentra el archivo de trucos: copia `R3MP01.txt` a `SD:/txtcodes/`, abre el gestor
   de trucos del juego en USB Loader GX, marca «CC Trilogy base pre1.0» y crea el GCT desde ahí (sale igual que el
   `R3MP01.gct`, comprobado).

## Instalar en Dolphin (por si quieres seguir probando ahí)
1. Copia `R3MP01.ini` en `Documentos\Dolphin Emulator\GameSettings\` (guarda antes el tuyo).
2. Activa **solo** «CC Trilogy base pre1.0» y deja «Habilitar trucos» activado.

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

**Cinemáticas:** mantener **+ 1 segundo** las salta en los tres juegos (sin cambios).

## Qué comprobar en la Wii
La lista de pruebas (la misma página) ya está puesta para la pre1.0: lo que fue bien en la n0.10 viene marcado, y hay
una sección nueva con lo propio de la Wii.
1. **Lo propio de la Wii:** arranca sin colgarse; los controles van en el menú de Trilogy; entrar y salir de MP1,
   MP2 y MP3 varias veces sin cuelgues; guardar y cargar.
2. **Lo que quedaba por probar:** gancho y látigo (cámara libre, columpiarse, tirar sin andar hacia atrás, la tensión),
   agitar, escáneres de ADN, hipermodo, otras cosas de meter y sacar, y qué hace la Y en el mapa de MP3.

Si algo se cuelga o los controles dejan de ir, dime en qué momento (y qué tipo de gancho tenías puesto).
