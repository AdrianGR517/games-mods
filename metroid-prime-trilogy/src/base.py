"""Mod Classic Controller para Metroid Prime Trilogy (R3MP01): generador del código Gecko.

Un solo código Gecko (comprimido, ver final()). El código común se escribe una vez y vale para los tres juegos y el menú:

  C0 (no se ejecuta: empieza con blr)   núcleo común + función de saltar cinemáticas + constantes + tabla de botones
  bloque de cada juego (2046D340 firma + 20006138 guarda ... E0):
      parches fijos del juego (cámara FPS de PrimeHack, Nunchuk/extensión, bola muelle, cinemáticas vistas)
      C2 en la lectura del mando: r3 = estado del mando, r4 = FICHA del juego (solo datos), bl núcleo
      C2 en la consulta de saltar cinemática: llama a la original y luego a la función común
      C2 en el menú HOME de la Wii: avisa al núcleo de que está abierto (entonces funciona como un menú más)

Los bl entre los C2 y el C0 son relativos y todo va en el mismo código, así que funciona esté donde esté en la
lista de Dolphin (aunque haya otros códigos activados delante).

Controles:
  Menús:    stick izq. = puntero (el derecho no hace nada), A/R = aceptar, B/ZL = atrás, cruceta = cruceta.
  Juego:    stick izq. = mover, stick der. = cámara con la mira centrada, A/R = disparar, ZR = misil, L = fijar,
            B/ZL = saltar, Y = morfosfera, − = mapa (MP1/MP2) o pausa (MP3), + = pausa (MP1/MP2) o hipermodo (MP3).
  Morfosfera: A/R = bomba, X = salto (bola muelle: una sola sacudida por pulsación), B/ZL = impulso,
            L = aracnosfera, ZR = bomba de energía, Y = salir. (Son los mismos botones del Wiimote que al jugar.)
  Cinemáticas: mantener + 1 s la salta en los tres juegos. En una cinemática el + no hace nada más, y si se sigue
            manteniendo después, no cuenta hasta que se suelta.
"""
import os, struct, keystone

ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC32 | keystone.KS_MODE_BIG_ENDIAN)
VERSION = "pre1.0"
LIMIT = 3272                       # bytes que caben en Dolphin (cabecera + códigos + final)
# La lista va comprimida dentro de un C0 (compresor, descompresor y armado: packer.py,
# unpack_asm.py, build_gct.py). Se descomprime en la tabla TRK (LIST = 0x80004180) cuando falla su suma de control.
# NOCOMP=1 genera la lista sin comprimir (para comparar).
COMPRESS = os.environ.get('NOCOMP') is None
CODE0 = 0x80002340                 # dirección de la primera línea si este es el primer código (solo para pruebas)

# --- botones ---------------------------------------------------------------------------------------------------
CL = {'UP': 0x0001, 'LEFT': 0x0002, 'ZR': 0x0004, 'X': 0x0008, 'A': 0x0010, 'Y': 0x0020, 'B': 0x0040, 'ZL': 0x0080,
      'R': 0x0200, 'PLUS': 0x0400, 'HOME': 0x0800, 'MINUS': 0x1000, 'L': 0x2000, 'DOWN': 0x4000, 'RIGHT': 0x8000}
WM = {'LEFT': 0x0001, 'RIGHT': 0x0002, 'DOWN': 0x0004, 'UP': 0x0008, 'PLUS': 0x0010, '2': 0x0100, '1': 0x0200,
      'B': 0x0400, 'A': 0x0800, 'MINUS': 0x1000, 'Z': 0x2000, 'C': 0x4000, 'HOME': 0x8000}

# Tabla de botones (clásico -> Wiimote). Una entrada = (botón del Wiimote << 16) | botones del clásico | contextos.
# Cada entrada lleva los contextos en los que vale (bits libres: 0x20/0x40/0x80 del Wiimote y 0x100 del
# clásico; el núcleo los quita antes de mandar el botón). El + manda el botón de pausa de cada juego (ficha 'pbtn'),
# que el núcleo escribe en su entrada antes de usar la tabla.
#   menú:  cruceta = cruceta, solo A acepta y solo B vuelve
#   pausa de MP1: cruceta izq./der. = − / + del Wiimote (opciones / banco de datos)
#   mapa (MP1, MP2): cruceta arriba/abajo = + / − (zoom), L = Z (L + stick izq. = mover), stick izq. = girar y puntero
#   juego: A/R, B/ZL, L, ZR, Y
P2 = P3 = True                     # cruceta en la pausa de MP1 / controles del mapa (para medir lo que ocupa cada uno)
# La mano de MP3 usa la zona muerta del stick (ADZ): sin ella, la vuelta del stick al centro (que se pasa un poco al
# otro lado) movía la mano hacia atrás al soltarlo.
# En el aviso de salir de la partida de MP1 (CQuitScreen, dentro de la pausa) la cruceta izq./der. vuelve a ser la del
# Wiimote: un C2 en su ProcessUserInput (0x80154DA0) usa el aviso del menú HOME (tabla de menús).
# Mapa de MP3: stick izq. = solo puntero, stick der. = girar, L + stick der. = desplazar (L = Z).
# MP1 y MP2 giran el mapa con el stick izquierdo.
MAP_RS = True                      # en el mapa de MP3 (aviso V_MAPC), stick der. = stick del Nunchuk
MAP_MP3 = True                     # mapa de MP3 con el aviso del C2 en MP3_MAP_HOOK
# Ruletas: tras WHEEL_CENTER_FRAMES (0,7 s) sin tocar el stick der., el puntero vuelve al centro
WHEEL_CENTER_FRAMES = 42
# Ruletas: jugando, cruceta arriba = − del Wiimote mantenido (ruleta de visores, los
# tres juegos) y cruceta abajo = + mantenido (ruleta de rayos, solo MP1/MP2). Sin ficha: la cruceta abajo manda el + del
# Wiimote solo si el + del clásico no lo usa ya (MP1/MP2: + = 2 = pausa; MP3: + = hipermodo, no hay rayos). Mientras se mantiene (y el frame en que se suelta, que es cuando el juego elige) la cámara
# no se mueve y el stick derecho lleva el puntero con imanes: se pega a la opción hacia la que apunta (arriba o abajo a
# un lado); sin tocarlo se queda donde estaba (al abrir, en el centro = visor/rayo normal).
WHEEL = True
# MP3, secciones "con la mano" (consolas, paneles, códigos): jugando con la
# cámara libre, si el juego no deja moverse a Samus (orden 0 desactivada en el ControlMapper del jugador, ficha 'abil'),
# el stick izquierdo mueve la mano (relativo, se queda al soltar, con límites) y el derecho sigue moviendo la cámara.
HAND = True
INT_SENS = MENU_SENS_HAND = 0.020   # velocidad de la mano con el stick a tope
INT_LIM_X, INT_LIM_Y = 0.50, 0.55   # límites de la mano (los mismos que el puntero del juego)
HAND_SOFT = 0.10                   # en los últimos 0,10 hacia el tope horizontal la mano frena poco a poco (si se
                                   # para de golpe en el tope, el juego sigue un poco y vuelve: rebote en los lados)
# Controles de movimiento de MP3 (parches de PrimeHack para Trilogy PAL):
# - gancho/látigo: L + X lo lanza; con el látigo enganchado, el stick izq. hacia abajo tira (+LASSO_STEP por frame;
#   al llegar a 1 se arranca); si no, la tensión baja;
# - agitar (quitarse enemigos de encima): mantener X;
# - cerraduras de combinación y escáneres ADN: stick izq. a los lados (±ROT, todo o nada pasado la mitad);
# - palancas, asas, sacar/meter (CScriptContextSensitiveAction, vive en un RSO): con la mano, stick izq. en la
#   dirección de cada paso (±LEVER_STEP por frame pasado la mitad).
CYCLE = True                       # MP1/MP2, cruceta izq./der. jugando = rayo anterior/siguiente (saltando los que no tienes)
GESTOS = True
G_LASSO = G_SHAKE = G_LOCKS = G_LEVERS = True   # por partes, para medir lo que ocupa cada una
LASSO_STEP, LEVER_STEP = 0.045, 0.050
MOTION_VF = 0x802e0a88             # TypesMatch__29CScriptContextSensitiveActionCFi (selfile.sel)
F = {'menu': 0x00800000, 'map': 0x00400000, 'pause': 0x00200000, 'game': 0x00000100}
F['all'] = sum(F.values())
def table_def():
    T = [('UP', 'UP', 'menu pause'), ('DOWN', 'DOWN', 'menu pause'), ('LEFT', 'LEFT', 'menu map'),
         ('RIGHT', 'RIGHT', 'menu map')]
    if P3: T += [('UP', 'PLUS', 'map'), ('DOWN', 'MINUS', 'map')]   # Y = leyenda = C (la entrada de jugar vale también en el mapa)
    if P2: T += [('LEFT', 'MINUS', 'pause'), ('RIGHT', 'PLUS', 'pause')]
    T += [('A', 'A', 'menu map pause'), ('B', 'B', 'menu map pause'), ('R|A', 'A', 'game'), ('B|ZL', 'B', 'game'),
          ('MINUS', '1', 'all'), ('HOME', 'HOME', 'all'), ('PLUS', None, 'all'),
          ('L', 'Z', 'map game' if P3 else 'game'), ('ZR', 'DOWN', 'game'), ('Y', 'C', 'map game' if P3 else 'game')]
    if WHEEL: T += [('UP', 'MINUS', 'game'), ('DOWN', 'PLUS', 'game')]   # la última: el núcleo pone 0 en MP3 (ver arriba)
    return T
def tmask(s): return sum(CL[b] for b in s.split('|'))
def fmask(s): return sum(F[c] for c in s.split())
def table():
    T = table_def()
    return [(WM[w] if w else 0) << 16 | tmask(c) | fmask(f) for c, w, f in T], [c for c, w, f in T].index('PLUS')
def wdn_idx(): return len(table_def()) - 1     # entrada de la ruleta de rayos (cruceta abajo)
PFLAGS = F['all'] >> 16 & 0xffff   # contextos del + (parte alta), que van con el botón de pausa de la ficha

# --- ajustes (los mismos que el mod de Metroid Prime 3) ------------------------------------------------------------------------
YAW_RATE, PITCH_RATE, AXIS_DZ, PITCH_MAX = 0.060, 0.040, 0.12, 1.52
DZ = 0.15                          # zona muerta del puntero de menús
MENU_SENS, MENU_BASE, MENU_SMOOTH, MENU_LIM_X = 0.020, 0.45, 0.35, 0.80
MENU_ASPECT = 16 / 9
SKIP_HOLD_S = 1.0                  # mantener + este tiempo salta la cinemática
TB = 60750000                      # time base de Wii (243 MHz / 4)
SPRING_FRAMES = 4                  # bola muelle: frames de "sacudida" por cada pulsación de X
CNT = 12                           # 0,2 s: cinemática hace poco / menú HOME abierto

K = [('ONE', 1.0), ('ZERO', 0.0), ('HALF', 0.5), ('SIXTH', 1 / 6), ('INV24', 1 / 24), ('TINY', 1e-7), ('SY', -1.0),
     ('DZ2', DZ * DZ), ('ADZ', AXIS_DZ), ('YAW', YAW_RATE), ('PITCH', PITCH_RATE), ('PMAX', PITCH_MAX), ('PMIN', -PITCH_MAX),
     ('MSENS', MENU_SENS), ('MBASE', MENU_BASE), ('MCUR', 1 - MENU_BASE), ('MSM', MENU_SMOOTH),
     ('MSX', MENU_ASPECT ** -0.5), ('MSY', -(MENU_ASPECT ** 0.5)), ('MLX', MENU_LIM_X)]
# Posiciones de las opciones de las ruletas (medidas en capturas de MP3; las de MP1/MP2 son iguales). En coordenadas del stick (y+ = arriba): lados (±WSX, WSY), arriba (0, WTY), centro (0, 0).
WHEEL_SIDE_X, WHEEL_SIDE_Y, WHEEL_TOP_Y = 0.202, -0.168, 0.388
if WHEEL: K += [('WSX', WHEEL_SIDE_X), ('WSY', WHEEL_SIDE_Y), ('WTY', WHEEL_TOP_Y)]
if GESTOS: K += [('LSTEP', LASSO_STEP), ('LEVER', LEVER_STEP)]
if HAND: K += [('HSOFT', 1 / HAND_SOFT)]
ROT_RATE = PITCH_RATE              # giro de cerraduras (0,04 como PrimeHack): se usa la constante del pitch
KO = {n: 4 * i for i, (n, _) in enumerate(K)}
TAB = 4 * len(K)                   # la tabla de botones va detrás de las constantes
def f2u(v): return struct.unpack('>I', struct.pack('>f', v))[0]

# --- variables: hueco de ceros de los 4 .dol (tabla del depurador TRK, 0x80004134-0x80006068) -------------------
VAR = 0x80005900
V = VAR & 0xffff
V_CLHOLD, V_SKIPT, V_SKIPON, V_PBLK, V_SPRC = 0x1c, 0x20, 0x24, 0x28, 0x2c
V_ACCF, V_ACC, V_RX, V_RY, V_PX, V_PY, V_VX, V_VY = 0x44, 0x48, 0x54, 0x58, 0x5c, 0x60, 0x78, 0x7c
V_LASSO, V_HANDX, V_HANDY, V_ROT = 0x08, 0x0c, 0x10, 0x14   # estado del látigo, tensión (x, x/4), giro
V_SPRING = 0x84                    # (byte) lo leen los parches de bola muelle
V_CYC = 0x18                       # petición de cambio de rayo (-1 / +1)
V_CUTC, V_HBMC, V_MAPC, V_WT = 0x30, 0x34, 0x38, 0x3c   # contadores seguidos; V_WT = frames sin stick en la ruleta
MAPCNT = 4                         # MP3: frames que dura el aviso de "mapa abierto" (el juego lo renueva cada frame)

# --- ficha de cada juego (solo datos; r30 en el núcleo) ---------------------------------------------------------
# palabras (direcciones): pl1 = dónde está el jugador, menu = byte distinto de 0 en menús (pausa, mapa...),
#   ing = palabra que debe valer 1 para estar jugando (0 = no mirar), lock = byte de blanco fijado,
#   arms = dirección del pitch del arma (0 = usar arm1/arm2), curb = base del cursor de la mira
# medias palabras (desplazamientos dentro del jugador, 0 = no hay): pl2 = segundo salto hasta el jugador,
#   pbtn = botón del Wiimote para el + del clásico, ball = morfosfera, move = en el aire (bola muelle solo en el suelo),
#   ctl = estado de control (MP3: si no es 1, puntero), orb = estado de órbita,
#   orb2 = (orbl << 8) | orbv en bytes: orbl = valor "sin cámara" (0xFF = no hay), orbv = valor "cámara libre aunque esté
#   fijado" (gancho/látigo); abil = byte del jugador que vale 0 en las secciones con la mano (0 = no hay: lee el
#   primer byte del jugador, que es el de su vtable, 0x80),
#   pitch, xf (matriz), angmom, angvel, angk = constante que se escribe en angmom/angvel, arm1/arm2 = arma,
#   mpv = valores del byte de menú: (mapa << 8) | pausa con pestañas. Contexto mapa = byte de 1 hasta "mapa"
#   (MP2: 3 = mapa y pausa, que también enseña el mapa); 0 = no hay
PW = ['pl1', None, 'menu', 'ing', 'lock', 'arms', 'curb']      # None = hueco de pl2/pbtn (medias palabras)
PH = ['ball', 'move', 'ctl', 'orb', 'orb2', 'pitch', 'xf', 'angmom', 'angvel', 'angk', 'arm1', 'arm2', 'mpv']
if HAND: PH += ['abil']
P = {k: 4 * i for i, k in enumerate(PW) if k}
P['pl2'], P['pbtn'] = 4, 6
P.update({k: 4 * len(PW) + 2 * i for i, k in enumerate(PH)})
P_LEN = 4 * len(PW) + 2 * len(PH)

def ficha(d, short=False):
    d = dict(d, orb2=(d.get('orbl', 0) & 0xff) << 8 | d.get('orbv', 0))
    b = struct.pack('>IHH', d['pl1'], d.get('pl2', 0), d['pbtn'] | PFLAGS)
    if not short:
        b += b''.join(struct.pack('>I', d.get(k, 0)) for k in PW[2:])
        b += b''.join(struct.pack('>H', d.get(k, 0)) for k in PH)
    b += b'\0' * (-len(b) % 4)
    return b

SM1, SM2 = 0x804c3360, 0x804ee738   # CStateManager de MP1 / MP2
GAMES = {
  'MP3': dict(sig=0x3a800000, guard=0x3CC0804B, khook=0x803c0360, kreg=29, korig="lfs 0,0xca0(28)", ext=0x803c266c,
              hbm=(0x800cc05c, "lwz 12,0x50(30)"), spring=0x8010712c, skip=(0x800b9f30, 0x800df018, 0x80062158),
              f=dict(pl1=0x805ca0e8, pl2=0x2184, pbtn=WM['PLUS'], menu=0x805cc1d7, lock=0x805ca237, curb=0x80673588,
                     ball=0x358, ctl=0x3aec, orb=0x370, orbl=1, orbv=2, pitch=0x784, xf=0x3c, abil=0x35dc,
                     angmom=0x174, angvel=0x174, angk=KO['TINY'])),
  'MP1': dict(sig=0x7c962378, guard=0x3CC0803A, khook=0x80331b38, kreg=29, korig="lfs 0,0xca0(28)", ext=0x80333e54,
              hbm=(0x800df018, "lwz 12,0x4c(30)"), quit=(0x80154da0, "stwu 1,-0x10(1)"),
              beam=dict(at=0x8018e844, orig="cmpwi 26,-1", gun=30, cur=0x310, beamreg=26, pidreg=25, order=0x00020103,
                        pa="  lis 6,0x804c\n  lwz 6,0x3c14(6)\n  cmpwi 6,0\n  bge cz1\n  lwz 6,0(6)\ncz1:\n", size=8, off=0x30),
              spring=0x80147830, skip=(0x800cf174, 0x8010822c, 0x802fc248),
              f=dict(pl1=SM1 + 0x84c, pbtn=WM['2'], menu=SM1 + 0x117c + 3, mpv=0x0102, lock=SM1 + 0xc93, arms=0x804c502c,
                     curb=0x805c6c2c, ball=0x2f4, move=0x25c, orb=0x300, orbl=0xffff, orbv=5, pitch=0x3dc, xf=0x2c,
                     angmom=0x118, angvel=0x154, angk=KO['ZERO'])),
  'MP2': dict(sig=0x80830000, guard=0x3CC0803D, khook=0x8034e4d4, kreg=25, korig="lfs 0,0(24)", ext=0x80350804,
              hbm=(0x800cf2c8, "lwz 12,0x4c(3)"),
              beam=dict(at=0x8018e4e4, orig="cmpwi 31,-1", gun=27, cur=0x768, beamreg=31, pidreg=30, order=0x00010203,
                        pa="  lis 6,0x804f\n  lwz 6,-0x3d4(6)\n  cmpwi 6,0\n  bge cz2\n  lwz 6,0x12ec(6)\ncz2:\n", size=12, off=0x5c),
              spring=0x8010d44c, skip=(0x800bdb9c, 0x800e9744, 0x80071c34),
              f=dict(pl1=SM2 + 0x14f4, pbtn=WM['2'], menu=SM2 + 0x2c0c + 3, mpv=0x0300, ing=SM2 + 0x153c, lock=SM2 + 0x1667,
                     curb=0x805d2d30, ball=0x374, move=0x2c4, orb=0x390, orbl=0xffff, orbv=5, pitch=0x5f0, xf=0x20,
                     angmom=0x178, angvel=0x178 + 0x18, angk=KO['ZERO'], arm1=0xea8, arm2=0x3b0 + 0x24)),
  'FE':  dict(sig=0x7c0000d0, guard=0x3CC08046, khook=0x80372e4c, kreg=29, korig="lfs 0,0xca0(28)", ext=0x80375158,
              hbm=(0x800a1674, "lwz 12,0x50(30)"),
              f=dict(pl1=0x80000000, pbtn=WM['1'])),        # *(0x80000000) = ID del disco (positivo) = sin jugador
}
# Parches fijos de cámara (PrimeHack, direcciones PAL de Trilogy verificadas): el juego deja de girar la cámara con el
# puntero y de escribir el pitch y el giro, para que lo haga el núcleo.
CAM = {
  'MP3': [(0x80080ac0, 0xec010072), (0x8014d9e0, 0x60000000), (0x8014d9b8, 0x60000000), (0x80133c74, 0x60000000),
          (0x801332bc, 0x60000000), (0x80080d44, 0x60000000), (0x8007fdc8, 0x480000e4), (0x8017f1d8, 0x60000000),
          (0x80016f48, 0x48000120)],
  'MP1': [(0x80099070, 0xec010072), (0x800992c4, 0x60000000), (0x80183cfc, 0x60000000), (0x80183d24, 0x60000000),
          (0x801768b4, 0x60000000), (0x804e1f38 + 0x134, 0x3fc28f5c)],
  'MP2': [(0x8008e30c, 0xc0430184), (0x8008e360, 0x60000000), (0x801496e4, 0x60000000), (0x8014970c, 0x60000000),
          (0x80137240, 0x60000000), (0x8008d18c, 0x60000000), (0x8008d15c, 0x60000000), (0x80145474, 0x48000050)],
}
# MP3: el mapa no tiene byte propio. 0x80161594 (lwz r3,0x7bc(r29)) solo se ejecuta con la pausa en la pantalla del
# mapa (gestor de la GUI +0x89C = 2): ahí se avisa. En Trilogy el mapa de la pausa es la MapScreen
# (SMapScreenWebInterface, en +0x7C0); 0x801615D4 solo corre si +0x7C0 = 0, así que no sirve.
MP3_MAP_HOOK = (0x80161594, "lwz 3,0x7bc(29)")
# MP3: estado de control (PrimeHack). En 0x8000AB58 (stw r6,0x78(r3)) el juego no lo escribe si el objeto es el jugador.
MP3_CTRL_HOOK = 0x8000ab58
MP3_CTRL_SRC = """  lis 3,0x805d
  addi 3,3,-0x5f40
  lwz 3,0x2c(3)
  lwz 3,4(3)
  lwz 3,0x2184(3)
  cmpw 3,31
  beq 0x20
  stw 6,0x78(31)
"""

# Parches fijos de los controles de movimiento de MP3 (los de PrimeHack para Trilogy PAL, comprobados en
# rs5mp3_p.dol, con nuestras variables). Los lee/escribe el núcleo (gest_src).
MP3_LASSO_F1 = 0x800dde44          # ProcessGrappleLasso (empieza en 0x800DDE0C)
MP3_LASSO_F2 = 0x8017063c          # animación del brazo tirando
MP3_LASSO_F3 = 0x80171424          # "¿lanzar el látigo?" (orden 0x1C del ControlMapper)
MP3_SLIDE = 0x8017ebec             # deslizarse por el gancho
MP3_LOCKS = (0x801f7b54, 0x801f9d6c)   # cerradura de combinación y escáner ADN: mtctr r12 ... bctrl (+8)
MP3_SHAKE = (0x800a8fc0, "li 26,0")    # agitar: r26 = mantener X
def mp3_gest():
    """(escrituras fijas, código del C2 de agitar)"""
    def w1(src): return int.from_bytes(asm(src, 0), 'big')
    hx, hy, hl, hr = V + V_HANDX, V + V_HANDY, V + V_LASSO, V + V_ROT
    pw = []
    f1 = MP3_LASSO_F1
    if not G_LASSO: return mp3_gest_rest(pw)
    pw += [(f1, w1("lis 11,0x8000")), (f1 + 8, 0x40800158), (f1 + 0xc, w1(f"lfs 2,0x{hx:x}(11)")),
           (f1 + 0x18, 0x40810148), (f1 + 0x54, 0x4800010c),
           (f1 + 0x160, w1("lis 30,0x8000")), (f1 + 0x164, w1(f"lwz 30,0x{hl:x}(30)")), (f1 + 0x168, 0x60000000)]
    f2 = MP3_LASSO_F2   # f0 = tensión (la guarda en +0x1CC el stfs original de +0x1C), f2 = tensión/4 -> +0x1C8
    pw += [(f2, w1("lis 11,0x8000")), (f2 + 4, w1(f"lfs 0,0x{hx:x}(11)")), (f2 + 8, w1(f"lfs 2,0x{hy:x}(11)")),
           (f2 + 0xc, 0x60000000), (f2 + 0x14, 0x60000000), (f2 + 0x18, 0x60000000)]
    # lanzar = L + X mantenidos (V_CLHOLD = botones del clásico)
    LX = f"""  lis 3,0x8000
  lhz 3,0x{V + V_CLHOLD + 2:x}(3)
  rlwinm 0,3,{32 - CL['L'].bit_length() + 1},31,31
  rlwinm 3,3,{32 - CL['X'].bit_length() + 1},31,31
  and 3,3,0
  blr
"""
    pw += [(MP3_LASSO_F3 + 4 * i, int.from_bytes(b, 'big')) for i, b in enumerate(words(LX))]
    sl = words("""  nop
  nop
  nop
  lfs 0,0x240(1)
  stfs 0,0x48(31)
  lfs 0,0x244(1)
  stfs 0,0x58(31)
  lfs 0,0x248(1)
  stfs 0,0x68(31)
  mr 3,31
  addi 4,31,0x3c
""")
    pw += [(MP3_SLIDE + 4 * i, int.from_bytes(b, 'big')) for i, b in enumerate(sl)]
    return mp3_gest_rest(pw)
def mp3_gest_rest(pw):
    def w1(src): return int.from_bytes(asm(src, 0), 'big')
    hr = V + V_ROT
    if G_LOCKS:
      for a in MP3_LOCKS: pw += [(a, w1("lis 12,0x8000")), (a + 8, w1(f"lfs 1,0x{hr:x}(12)"))]
    shake = G_SHAKE and f"""  lis 26,0x8000
  lbz 26,0x{V + V_CLHOLD + 3:x}(26)
  rlwinm 26,26,{32 - CL['X'].bit_length() + 1},31,31
"""
    return pw, shake

# =====================================================================================================
# Código común
# =====================================================================================================
ROT6 = ''.join(f"""  lfs 1,{4*j}(6)
  lfs 2,{16+4*j}(6)
  fmuls 5,12,1
  fnmsubs 5,11,2,5
  fmuls 6,11,1
  fmadds 6,12,2,6
  stfs 5,{4*j}(6)
  stfs 6,{16+4*j}(6)
""" for j in range(3))   # gira la matriz del jugador alrededor de Z (filas X e Y, columnas 0..2); base r6

def clamp(reg, lim_hi, lim_lo_neg=True):
    """reg = min(reg, f13) y max(reg, -f13) con f13 = límite. Usa f11, f12."""
    return f"""  fsubs 11,13,{reg}
  fsel {reg},11,{reg},13
  fneg 11,13
  fsubs 12,{reg},11
  fsel {reg},12,{reg},11
"""

def core_src():
    PLUS, X, HOME = CL['PLUS'], CL['X'], CL['HOME']
    TABLE, T_PLUS_IDX = table()
    ncnt = 3 if P3 and MAP_MP3 else 2   # contadores seguidos: cinemática, menú HOME, mapa de MP3
    menu_src = f"""  lwz 3,{P['menu']}(30)
  lbz 3,0(3)
  cmpwi 3,0
"""
    if not (P2 or P3): menu_src += "  bne ctxnone\n"
    else:
        menu_src += "  beq notmenu\n"
        if P2: menu_src += f"""  lbz 0,{P['mpv'] + 1}(30)
  cmpw 3,0
  bne nopause
  lis 26,0x{F['pause'] >> 16:x}
nopause:
"""
        if P3: menu_src += f"""  lbz 0,{P['mpv']}(30)
  cmplw 0,3,0
  bgt ctxnone
ctxmap:
  lis 26,0x{F['map'] >> 16:x}
"""
        menu_src += "  b ctxnone\nnotmenu:\n"
    mapc_src = f"""  lwz 3,{V_MAPC}(8)
  cmpwi 3,0
  bne ctxmap
""" if P3 and MAP_MP3 else ""
    mapst_src = f"""  lwz 0,{V_MAPC}(8)
  cmpwi 0,0
  beq nomapst
  stfs 3,0x60(29)
  stfs 4,0x64(29)
nomapst:
""" if P3 and MAP_RS else ""
    UP = CL['UP']
    # Mano (MP3). abil = byte del ControlMapper del jugador (+0x35D8 + 4 = orden 0 activada); 0 = sin moverse.
    # La mano va en RX/RY (como la mira): se suma el stick izq. y se limita; en el resto del modo FPS vale 0.
    hand_src = f"""  lhz 3,{P['abil']}(30)
  lbzx 3,28,3
  cmpwi 3,0
  bne notint
  fabs 5,1
  fsubs 5,5,13
  fsel 1,5,1,8
  fabs 5,2
  fsubs 5,5,13
  fsel 2,5,2,8
  lfs 6,{KO['MSENS']}(7)
  lfs 13,{KO['HALF']}(7)
  lfs 10,{V_RX}(8)
  fabs 5,10
  fsubs 11,13,5
  lfs 12,{KO['HSOFT']}(7)
  fmuls 11,11,12
  lfs 12,{KO['ONE']}(7)
  fsubs 9,11,12
  fsel 11,9,12,11
  fmuls 9,1,10
  fsel 11,9,11,12
  fmuls 11,11,6
  fneg 12,13
  fmadds 10,1,11,10
  fsubs 11,13,10
  fsel 10,11,10,13
  fsubs 11,10,12
  fsel 10,11,10,12
  stfs 10,{V_RX}(8)
  lfs 13,{KO['MCUR']}(7)
  fneg 12,13
  lfs 10,{V_RY}(8)
  fmadds 10,2,6,10
  fsubs 11,13,10
  fsel 10,11,10,13
  fsubs 11,10,12
  fsel 10,11,10,12
  stfs 10,{V_RY}(8)
  b rdone
notint:
""" if HAND else ""
    # Controles de movimiento de MP3 (solo jugando y solo en MP3: es el único con 'abil' en la ficha). Lo leen los
    # parches fijos de MP3 (ver MP3_GEST). f13 = 0,5 todo el rato.
    # - giro de cerraduras/ADN: V_ROT = ±ROT_RATE con el stick izq. a un lado pasado la mitad, si no 0
    # - látigo (blanco fijado de tipo orbv = 2): tensión en V_HANDX, sube LSTEP por frame con el stick izq. abajo
    #   (pasado la mitad) y si no baja; V_LASSO = 2, o 4 (arrancado) al llegar a 1; sin látigo, 0. V_HANDY = tensión / 4
    # - palancas/asas: con el stick izq. pasado la mitad, recorre la lista de objetos y a cada
    #   CScriptContextSensitiveAction agarrada (estado 3) le suma ±LEVER a su avance (+0x154) según el stick en el eje de
    #   su paso. Según RSO_ScriptContextSensitiveAction.rso, el tipo de gesto es +0x1E4 (0 = meter/sacar ->
    #   stick adelante/atrás; 1 y 2 = girar -> stick a los lados, con el signo de x cambiado) y el signo, +0x1E8.
    gest_src = f"""  cmpwi 26,0x{F['game']:x}
  bne gdone
  lhz 3,{P['abil']}(30)
  cmpwi 3,0
  beq gdone
  lfs 13,{KO['HALF']}(7)
""" + (f"""  fabs 5,1
  fsubs 5,5,13
  lfs 12,{KO['PITCH']}(7)
  fneg 6,12
  fsel 6,1,12,6
  fsel 6,5,6,8
  stfs 6,{V_ROT}(8)
""" if G_LOCKS else "") + (f"""  lhz 3,{P['orb']}(30)
  lwzx 3,28,3
  lbz 0,{P['orb2'] + 1}(30)
  fmr 9,8
  cmpw 3,0
  li 3,0
  bne lstore
  lfs 9,{V_HANDX}(8)
  lfs 12,{KO['LSTEP']}(7)
  fadds 5,2,13
  fsel 6,5,2,8
  stfs 6,0x64(29)
  fneg 6,12
  fsel 12,5,6,12
  fadds 9,9,12
  fsel 9,9,9,8
  fsubs 5,7,9
  fsel 9,5,9,7
  li 3,2
  fcmpu 0,9,7
  blt lstore
  li 3,4
lstore:
  stw 3,{V_LASSO}(8)
  stfs 9,{V_HANDX}(8)
  fmuls 9,9,13
  fmuls 9,9,13
  stfs 9,{V_HANDY}(8)
""" if G_LASSO else "") + (f"""  fabs 5,1
  fabs 6,2
  fadds 5,5,6
  fcmpu 0,5,13
  blt gdone
  lwz 3,{P['pl1']}(30)
  lwz 3,0(3)
  lwz 3,0x1010(3)
  cmpwi 3,0
  bge gdone
  addi 4,3,4
  li 0,2048
  mtctr 0
lv_loop:
  lwz 6,0(4)
  addis 12,6,-0x8000
  lis 11,0x0180
  cmplw 12,11
  bge lv_next
  lwz 10,0x38(6)
  andis. 0,10,0x0010
  bne lv_proc
  andis. 0,10,0x2000
  beq lv_next
  andis. 0,10,0x0020
  bne lv_next
lv_proc:
  lwz 5,0(6)
  addis 12,5,-0x8000
  cmplw 12,11
  bge lv_next
  lwz 5,0xc(5)
  lis 12,0x{MOTION_VF >> 16:x}
  ori 12,12,0x{MOTION_VF & 0xffff:x}
  cmplw 5,12
  bne lv_next
  lwz 5,0x14c(6)
  cmpwi 5,3
  bne lv_next
  lwz 5,0x1e4(6)
  cmpwi 5,0
  fmr 11,2
  beq lv_y
  fneg 11,1
lv_y:
  lfs 10,0x1e8(6)
  fneg 12,10
  fneg 9,11
  fsel 11,12,11,9
  fabs 5,11
  fsubs 5,5,13
  lfs 12,{KO['LEVER']}(7)
  fneg 6,12
  fsel 6,11,12,6
  fsel 6,5,6,8
  lfs 9,0x154(6)
  fadds 9,9,6
  fsel 9,9,9,8
  fsubs 5,7,9
  fsel 9,5,9,7
  stfs 9,0x154(6)
lv_next:
  lhz 5,6(4)
  cmplwi 5,0xffff
  beq gdone
  slwi 5,5,3
  add 4,3,5
  addi 4,4,4
  bdnz lv_loop
""" if G_LEVERS else "") + "gdone:\n" if GESTOS else ""
    assert not GESTOS or (ROT_RATE == dict(K)['PITCH'] and HAND)
    assert not HAND or (dict(K)['MSENS'] == INT_SENS and dict(K)['HALF'] == INT_LIM_X and abs(dict(K)['MCUR'] - INT_LIM_Y) < 1e-9)
    # Botón del Wiimote de la ruleta de rayos (cruceta abajo) = + del Wiimote si el + del clásico manda otro
    # (bit 0x100 = 2 del Wiimote en 'pbtn' -> 0x10), si no 0 (MP3)
    # La entrada cruceta abajo (jugando) = el + en MP1/MP2 (pbtn = 2: ruleta de rayos) y el 2 en MP3 (pbtn = +):
    # la pista. r3 = pbtn con los bits de contexto (0xE0), así que se sacan los dos bits sueltos. El menú no la usa.
    wpatch = f"""  rlwinm 0,3,28,27,27
  rlwimi 0,3,4,23,23
  sth 0,{TAB + 4 * wdn_idx()}(7)
""" if WHEEL else ""
    # Con la lista comprimida, las dos entradas que se parchean por juego vuelven a su valor de fábrica tras la tabla, para
    # que la suma de control de la lista no cambie cada frame (si cambiara, se descomprimiría cada frame)
    T0 = table()[0]
    trest = (f"""  li 0,0x{T0[T_PLUS_IDX] >> 16:x}
  sth 0,{TAB + 4 * T_PLUS_IDX}(7)
""" + (f"""  li 0,0x{T0[wdn_idx()] >> 16:x}
  sth 0,{TAB + 4 * wdn_idx()}(7)
""" if WHEEL else "")) if COMPRESS else ""
    # Cambio de rayo (MP1/MP2): jugando, cruceta izq./der. recién pulsada deja la petición -1/+1 en V_CYC (la gasta
    # el C2 de cada juego en el cambio de rayo, cyc_src); fuera de jugar se borra. MP3 y el menú no la leen.
    cyc_req = f"""  rlwinm 0,5,17,31,31
  rlwinm 3,5,31,31,31
  subf. 0,3,0
  cmpwi 1,26,0x{F['game']:x}
  bne 1,cyc0
  beq cycok
  b cycst
cyc0:
  li 0,0
cycst:
  stw 0,{V_CYC}(8)
cycok:
""" if CYCLE else ""
    # ruleta: cruceta arriba (o abajo, si hay ruleta de rayos) mantenida o recién soltada -> modo ruleta (r31 = 4)
    wcheck = f"""  or 3,4,6
  lhz 0,{P['pbtn']}(30)
  rlwinm 0,0,6,17,17
  ori 0,0,0x{UP:x}
  and. 3,3,0
  li 31,4
  bne ctxnone
  li 31,2
""" if WHEEL else ""
    wdisp = """  cmpwi 31,3
  bgt wheel
""" if WHEEL else ""
    # imanes: el stick derecho (si pasa de ~71%) elige la opción hacia la que apunta: arriba si y >= |x|/2 (unos 27°
    # sobre la horizontal), si no la de su lado. Sin tocarlo se queda donde estaba. Va al puntero y al cursor del juego.
    wcode = f"""wheel:
  fmuls 9,3,3
  fmadds 9,4,4,9
  lfs 13,{KO['HALF']}(7)
  fcmpu 0,9,13
  lwz 3,{V_WT}(8)
  addi 3,3,1
  bge wpush
  stw 3,{V_WT}(8)
  cmpwi 3,{WHEEL_CENTER_FRAMES}
  bge nocam
  b writecur
wpush:
  li 3,0
  stw 3,{V_WT}(8)
  fabs 5,3
  fmuls 5,5,13
  fsubs 5,4,5
  lfs 11,{KO['WSX']}(7)
  fneg 12,11
  fsel 11,3,11,12
  fsel 11,5,8,11
  lfs 12,{KO['WSY']}(7)
  lfs 13,{KO['WTY']}(7)
  fsel 12,5,13,12
  stfs 11,{V_RX}(8)
  stfs 12,{V_RY}(8)
  b writecur
""" if WHEEL else ""
    return f"""
core:
  stwu 1,-0x20(1)
  mflr 0
  stw 0,0x24(1)
  stmw 26,8(1)
  mr 29,3
  mr 30,4
  lis 8,0x{VAR >> 16:x}
  ori 8,8,0x{V:x}
  li 3,{ncnt}
  mtctr 3
  addi 12,8,{V_CUTC - 4}
cdec:
  lwzu 3,4(12)
  addic. 3,3,-1
  blt cz
  stw 3,0(12)
cz:
  bdnz cdec
  lbz 3,0x5c(29)
  cmpwi 3,2
  beq isclassic
  lwz 4,0(29)
  rlwinm 4,4,6,21,21
  stw 4,{V_CLHOLD}(8)
  b ret
isclassic:
  bl data_end
""" + "  trap\n" * (len(K) + len(TABLE)) + f"""
data_end:
  mflr 7
  lhz 3,{P['pbtn']}(30)
  sth 3,{TAB + 4 * T_PLUS_IDX}(7)
""" + wpatch + f"""  lwz 4,0x60(29)
  lwz 5,0x64(29)
  lwz 6,0x68(29)
  stw 4,{V_CLHOLD}(8)
  lwz 3,{V_PBLK}(8)
  lwz 0,{V_CUTC}(8)
  or. 3,3,0
  beq pfree
  andi. 3,4,0x{PLUS:x}
  stw 3,{V_PBLK}(8)
  li 0,0x{PLUS:x}
  andc 4,4,0
  andc 5,5,0
  andc 6,6,0
pfree:
  lwz 12,{V_SPRC}(8)
  cmpwi 12,0
  beq sp1
  addi 12,12,-1
sp1:
  andi. 0,5,0x{X:x}
  beq sp2
  li 12,{SPRING_FRAMES}
sp2:
  stw 12,{V_SPRC}(8)
  li 31,0
  lis 26,0x{F['menu'] >> 16:x}
  lwz 3,{V_HBMC}(8)
  cmpwi 3,0
  bne ctxnone
""" + mapc_src + f"""  lwz 3,{P['pl1']}(30)
  lwz 28,0(3)
  cmpwi 28,0
  bge ctxnone
  lhz 3,{P['pl2']}(30)
  cmpwi 3,0
  beq hp
  lwzx 28,28,3
  cmpwi 28,0
  bge ctxnone
hp:
""" + menu_src + f"""  lwz 3,{P['ing']}(30)
  cmpwi 3,0
  beq ingok
  lwz 3,0(3)
  cmpwi 3,1
  bne ctxnone
ingok:
  li 31,2
  li 26,0x{F['game']:x}
  lhz 3,{P['ball']}(30)
  lwzx 3,28,3
  cmpwi 3,0
  beq nomorph
  lhz 3,{P['move']}(30)
  cmpwi 3,0
  beq spok
  lwzx 3,28,3
  cmpwi 3,0
  bne ctxnone
spok:
  addic 0,12,-1
  subfe 12,0,12
  b ctxdone
nomorph:
""" + wcheck + f"""  lhz 3,{P['ctl']}(30)
  cmpwi 3,0
  beq ctlok
  lwzx 3,28,3
  cmpwi 3,0
  bge ctxnone
  lwz 3,0x7cc(3)
  cmpwi 3,1
  li 31,1
  bne ctxnone
  li 31,2
ctlok:
  lhz 3,{P['orb']}(30)
  lwzx 3,28,3
  lbz 0,{P['orb2']}(30)
  cmpw 3,0
  beq ctxnone
  lbz 0,{P['orb2'] + 1}(30)
  cmpw 3,0
  beq fpsok
  lwz 3,{P['lock']}(30)
  lbz 3,0(3)
  cmpwi 3,0
  bne ctxnone
fpsok:
  li 31,3
ctxnone:
  li 12,0
ctxdone:
  stb 12,{V_SPRING}(8)
  lwz 9,0(29)
  lwz 10,4(29)
  lwz 11,8(29)
  addi 12,7,{TAB - 4}
  li 3,{len(TABLE)}
  mtctr 3
tloop:
  lwzu 3,4(12)
  and. 0,3,26
  beq t3
  srwi 0,3,16
  andi. 0,0,0x{0xffff & ~(F['all'] >> 16):x}
  and. 27,4,3
  beq t1
  or 9,9,0
t1:
  and. 27,5,3
  beq t2
  or 10,10,0
t2:
  and. 27,6,3
  beq t3
  or 11,11,0
t3:
  bdnz tloop
""" + cyc_req + trest + f"""  stw 9,0(29)
  stw 10,4(29)
  stw 11,8(29)
  lfs 1,0x6c(29)
  lfs 2,0x70(29)
  lfs 3,0x74(29)
  lfs 4,0x78(29)
  lfs 7,{KO['ONE']}(7)
  lfs 8,{KO['ZERO']}(7)
  stfs 1,0x60(29)
  stfs 2,0x64(29)
""" + mapst_src + f"""  stfs 8,0x68(29)
  stfs 8,0x6c(29)
  stfs 8,0x70(29)
  stfs 8,0x74(29)
  stfs 8,0x78(29)
  stfs 8,0x28(29)
  stfs 8,0x2c(29)
  stfs 8,0x30(29)
  stfs 7,0x34(29)
  stfs 8,0x38(29)
  stfs 7,0x48(29)
  li 3,1
  stb 3,0x5c(29)
  li 3,2
  stb 3,0x5e(29)
  lwz 3,{V_ACCF}(8)
  cmpwi 3,0
  bne acc_have
  lfs 5,0x18(29)
  lfs 6,{KO['HALF']}(7)
  fcmpu 0,5,6
  blt acc_skip
  lwz 3,0xc(29)
  stw 3,{V_ACC}(8)
  lwz 3,0x10(29)
  stw 3,{V_ACC + 4}(8)
  lwz 3,0x14(29)
  stw 3,{V_ACC + 8}(8)
  li 3,1
  stw 3,{V_ACCF}(8)
acc_have:
  lwz 3,{V_ACC}(8)
  stw 3,0xc(29)
  lwz 3,{V_ACC + 4}(8)
  stw 3,0x10(29)
  lwz 3,{V_ACC + 8}(8)
  stw 3,0x14(29)
  stfs 7,0x18(29)
  stfs 8,0x1c(29)
acc_skip:
""" + gest_src + wdisp + f"""  cmpwi 31,2
  bgt fps
  beq nocam
  fmuls 9,1,1
  fmadds 9,2,2,9
  lfs 13,{KO['DZ2']}(7)
  fcmpu 0,9,13
  bge pmove
  stfs 8,{V_VX}(8)
  stfs 8,{V_VY}(8)
  b pset
pmove:
  fsubs 10,9,7
  fsel 9,10,7,9
  lfs 13,{KO['MCUR']}(7)
  lfs 10,{KO['MBASE']}(7)
  fmadds 9,9,13,10
  lfs 13,{KO['MSENS']}(7)
  fmuls 9,9,13
  lfs 13,{KO['MSM']}(7)
  lfs 12,{KO['MSX']}(7)
  fmuls 10,1,12
  fmuls 10,10,9
  lfs 11,{V_VX}(8)
  fsubs 12,10,11
  fmadds 11,12,13,11
  stfs 11,{V_VX}(8)
  lfs 10,{V_PX}(8)
  fadds 10,10,11
  lfs 12,{KO['MLX']}(7)
  fsubs 11,12,10
  fsel 10,11,10,12
  fneg 11,12
  fsubs 12,10,11
  fsel 10,12,10,11
  stfs 10,{V_PX}(8)
  lfs 12,{KO['MSY']}(7)
  fmuls 10,2,12
  fmuls 10,10,9
  lfs 11,{V_VY}(8)
  fsubs 12,10,11
  fmadds 11,12,13,11
  stfs 11,{V_VY}(8)
  lfs 10,{V_PY}(8)
  fadds 10,10,11
  fsubs 11,7,10
  fsel 10,11,10,7
  fneg 11,7
  fsubs 12,10,11
  fsel 10,12,10,11
  stfs 10,{V_PY}(8)
pset:
  lfs 9,{V_PX}(8)
  stfs 9,0x20(29)
  lfs 9,{V_PY}(8)
  stfs 9,0x24(29)
ret:
  lmw 26,8(1)
  lwz 0,0x24(1)
  mtlr 0
  addi 1,1,0x20
  blr
fps:
  lfs 13,{KO['ADZ']}(7)
  fabs 5,3
  fsubs 5,5,13
  fsel 3,5,3,8
  fabs 5,4
  fsubs 5,5,13
  fsel 4,5,4,8
""" + hand_src + f"""  stfs 8,{V_RX}(8)
  stfs 8,{V_RY}(8)
rdone:
  fabs 5,3
  fmuls 5,5,3
  lfs 13,{KO['YAW']}(7)
  fmuls 5,5,13
  fneg 5,5
  fabs 6,4
  fmuls 6,6,4
  lfs 13,{KO['PITCH']}(7)
  fmuls 6,6,13
  lhz 6,{P['pitch']}(30)
  lfsx 9,28,6
  fadds 9,9,6
  lfs 13,{KO['PMAX']}(7)
  fsubs 10,13,9
  fsel 9,10,9,13
  lfs 13,{KO['PMIN']}(7)
  fsubs 10,9,13
  fsel 9,10,9,13
  stfsx 9,28,6
  lwz 6,{P['arms']}(30)
  cmpwi 6,0
  beq armdyn
  stfs 9,0(6)
  b armdone
armdyn:
  lhz 6,{P['arm1']}(30)
  cmpwi 6,0
  beq armdone
  lwzx 6,28,6
  cmpwi 6,0
  bge armdone
  lhz 0,{P['arm2']}(30)
  stfsx 9,6,0
armdone:
  fmuls 10,5,5
  lfs 13,{KO['SIXTH']}(7)
  fmuls 11,10,13
  fmuls 11,11,5
  fsubs 11,5,11
  lfs 13,{KO['HALF']}(7)
  fmuls 12,10,13
  fsubs 12,7,12
  fmuls 10,10,10
  lfs 13,{KO['INV24']}(7)
  fmuls 10,10,13
  fadds 12,12,10
  lhz 6,{P['xf']}(30)
  add 6,28,6
""" + ROT6 + f"""  lhz 3,{P['angk']}(30)
  lfsx 13,7,3
  lhz 6,{P['angmom']}(30)
  stfsx 13,28,6
  lhz 6,{P['angvel']}(30)
  stfsx 13,28,6
  b writecur
nocam:
  stfs 8,{V_RX}(8)
  stfs 8,{V_RY}(8)
writecur:
  lfs 11,{V_RX}(8)
  lfs 12,{V_RY}(8)
  lfs 13,{KO['SY']}(7)
  fmuls 12,12,13
  stfs 11,0x20(29)
  stfs 12,0x24(29)
  lwz 10,{P['curb']}(30)
  lwz 10,0(10)
  cmpwi 10,0
  bge ret
  lwz 10,0xd04(10)
  cmpwi 10,0
  bge ret
  stfs 11,0x9c(10)
  stfs 12,0x15c(10)
  b ret
""" + wcode

def cyc_src():
    """Cambio de rayo con la cruceta (MP1/MP2), común. Lo llama el C2 del cambio de rayo de cada juego con
    r10 = rayo actual, r6 = inventario (si no es un puntero, nada), r5 = (tamaño de cada entrada << 16) | desplazamiento
    del "lo tienes", r9 = orden de los rayos (un byte cada uno). Gasta la petición de V_CYC y devuelve r4 = rayo nuevo
    (el siguiente que tengas en ese sentido) o -1. Usa r0, r3-r6, r8-r12 y ctr."""
    return f"""
cyc:
  lis 12,0x{VAR >> 16:x}
  lwz 11,{V + V_CYC}(12)
  li 4,-1
  cmpwi 11,0
  beqlr
  li 0,0
  stw 0,{V + V_CYC}(12)
  cmpwi 6,0
  bgelr
  andi. 0,5,0xffff
  add 6,6,0
  srwi 5,5,16
  li 8,0
cfind:
  slwi 3,8,3
  addi 3,3,8
  rlwnm 3,9,3,24,31
  cmpw 3,10
  beq cfound
  addi 8,8,1
  cmpwi 8,4
  blt cfind
  li 8,0
cfound:
  li 3,3
  mtctr 3
cstep:
  add 8,8,11
  andi. 8,8,3
  slwi 3,8,3
  addi 3,3,8
  rlwnm 3,9,3,24,31
  mullw 0,3,5
  lwzx 0,6,0
  cmpwi 0,0
  bne ctake
  bdnz cstep
  blr
ctake:
  mr 4,3
  blr
"""

def skip_src():
    """Saltar cinemáticas, común a los tres juegos. Se llama justo después de la consulta del botón de saltar del
    propio juego (r3 = lo que devolvió). Marca "en cinemática" (para que + no haga nada más) y devuelve r3 = 1 si el +
    del clásico (o el del Wiimote) lleva SKIP_HOLD_S pulsado. Solo usa r10-r12 y cr0."""
    t = int(SKIP_HOLD_S * TB)
    return f"""
skip:
  lis 12,0x{VAR >> 16:x}
  li 11,{CNT}
  stw 11,{V + V_CUTC}(12)
  mftb 10
  lwz 11,{V + V_CLHOLD}(12)
  andi. 11,11,0x{CL['PLUS']:x}
  beq sk_noplus
  lwz 11,{V + V_SKIPON}(12)
  cmpwi 11,0
  bne sk_have
  stw 10,{V + V_SKIPT}(12)
  li 11,1
  stw 11,{V + V_SKIPON}(12)
sk_have:
  lwz 11,{V + V_SKIPT}(12)
  subf 10,11,10
  lis 11,0x{t >> 16:x}
  ori 11,11,0x{t & 0xffff:x}
  cmplw 10,11
  bltlr
  li 3,1
  blr
sk_noplus:
  li 11,0
  stw 11,{V + V_SKIPON}(12)
  blr
"""

def asm(src, addr):
    e, _ = ks.asm(src, addr)
    return bytes(e)

def core_data():
    """constantes y tabla de botones (van detrás del bl data_end). Se meten después de ensamblar: keystone a veces
    falla al azar con muchos .long, así que en el código van como trap y aquí se sustituyen."""
    return b''.join(struct.pack('>I', f2u(v)) for _, v in K) + b''.join(struct.pack('>I', t) for t in table()[0])

def asm_core(addr):
    c = asm(core_src(), addr); d = core_data(); ph = bytes.fromhex('7FE00008') * (len(d) // 4)
    i = c.find(ph); assert i >= 0 and i % 4 == 0 and c.find(ph, i + 4) < 0
    return c[:i] + d + c[i + len(d):]

def words(src, addr=0):
    b = asm(src, addr)
    return [b[i:i + 4] for i in range(0, len(b), 4)]

def bl_rel(frm, to):
    return (0x48000001 | ((to - frm) & 0x03FFFFFC)).to_bytes(4, 'big')

def hexline(b8): return f"{b8[:4].hex().upper()} {b8[4:8].hex().upper()}"
def w04(a, v): return f"{0x04000000 | a & 0x1ffffff:08X} {v:08X}"

def c2_lines(addr, ws):
    ws = list(ws)
    if len(ws) % 2 == 0: ws.append(bytes.fromhex('60000000'))
    ws.append(b'\0' * 4)
    return [f"C2{addr & 0x1ffffff:06X} {len(ws) // 2:08X}"] + [hexline(ws[i] + ws[i + 1]) for i in range(0, len(ws), 2)]

def patch_lines(pw):
    """escrituras fijas: seguidas -> un 06, sueltas -> 04"""
    runs = []
    for a, v in sorted(pw):
        if runs and runs[-1][0] + 4 * len(runs[-1][1]) == a: runs[-1][1].append(v)
        else: runs.append((a, [v]))
    L = []
    for a, vs in runs:
        if len(vs) < 3: L += [w04(a + 4 * k, v) for k, v in enumerate(vs)]
        else:
            bs = b''.join(struct.pack('>I', v) for v in vs); n = len(bs); bs += b'\0' * (-n % 8)
            L.append(f"{0x06000000 | a & 0x1ffffff:08X} {n:08X}")
            L += [hexline(bs[k:k + 8]) for k in range(0, len(bs), 8)]
    return L

class Builder:
    def __init__(s): s.L = []
    def off(s, line): return 8 * line              # desplazamiento de una línea desde el principio del código
    def add_c2(s, addr, ws, rel=()):
        """rel: [(índice de palabra, destino como desplazamiento en el código)] -> bl relativo"""
        body = s.off(len(s.L) + 1)
        ws = list(ws)
        for i, to in rel: ws[i] = bl_rel(body + 4 * i, to)
        s.L += c2_lines(addr, ws)

def build():
    B = Builder()
    # --- C0 con el código común (no se ejecuta: la primera instrucción es blr) ---
    fbase = CODE0 + 8 + 4
    core = asm_core(fbase)
    skip = asm(skip_src(), fbase + len(core))
    cyc = asm(cyc_src(), fbase + len(core) + len(skip)) if CYCLE else b''
    body = bytes.fromhex('4E800020') + core + skip + cyc
    body += b'\0' * (-len(body) % 8)
    B.L.append(f"C0000000 {len(body) // 8:08X}")
    B.L += [hexline(body[i:i + 8]) for i in range(0, len(body), 8)]
    at = {'core': 8 + 4, 'skip': 8 + 4 + len(core), 'cyc': 8 + 4 + len(core) + len(skip)}
    sizes = {'comun': len(B.L) * 8}
    for g in ['MP3', 'MP1', 'MP2', 'FE']:
        G = GAMES[g]; n0 = len(B.L)
        B.L += [f"2046D340 {G['sig']:08X}", f"20006138 {G['guard']:08X}"]
        pw = [(G['ext'], 0x4182003C)] + CAM.get(g, [])
        if 'spring' in G: pw += [(G['spring'], 0x3C608000), (G['spring'] + 4, 0x88630000 | (V + V_SPRING))]
        if 'skip' in G: pw += [(G['skip'][0], 0x38600001), (G['skip'][0] + 4, 0x4E800020)]
        B.L += patch_lines(pw)
        # lectura del mando: r3 = estado, r4 = ficha, bl núcleo, instrucción original
        f = ficha(G['f'], short=(g == 'FE'))
        ws = words(f"  mr 3,{G['kreg']}\n  bl 0x{4 + 4 + len(f):x}\n") + [f[i:i + 4] for i in range(0, len(f), 4)]
        ws += words("  mflr 4\n") + [None] + words(f"  {G['korig']}\n")
        ws[1] = (0x48000001 | (4 + len(f))).to_bytes(4, 'big')           # bl por encima de la ficha
        B.add_c2(G['khook'], ws, rel=[(len(ws) - 2, at['core'])])
        if 'skip' in G:
            seen, hook, orig = G['skip']
            ws = words(f"  lis 12,0x{orig >> 16:x}\n  ori 12,12,0x{orig & 0xffff:x}\n  mtctr 12\n  bctrl\n") + [None]
            B.add_c2(hook, ws, rel=[(4, at['skip'])])
        if g == 'MP3': B.add_c2(MP3_CTRL_HOOK, words(MP3_CTRL_SRC))
        if g == 'MP3' and GESTOS:
            gpw, shake = mp3_gest()
            B.L += patch_lines(gpw)
            if shake: B.add_c2(MP3_SHAKE[0], words(shake))
        if g == 'MP3' and P3 and MAP_MP3:
            ma, morig = MP3_MAP_HOOK
            B.add_c2(ma, words(f"  lis 12,0x{VAR >> 16:x}\n  li 0,{MAPCNT}\n  stw 0,{V + V_MAPC}(12)\n  {morig}\n"))
        if CYCLE and 'beam' in G:
            Bm = G['beam']
            pre = words(Bm['pa'] + f"  lwz 10,0x{Bm['cur']:x}({Bm['gun']})\n  lis 5,{Bm['size']}\n  ori 5,5,0x{Bm['off']:x}\n"
                        f"  lis 9,0x{Bm['order'] >> 16:x}\n  ori 9,9,0x{Bm['order'] & 0xffff:x}\n")
            post = words(f"  cmpwi 4,0\n  blt cnone\n  mr {Bm['beamreg']},4\n  mr {Bm['pidreg']},4\ncnone:\n  {Bm['orig']}\n")
            B.add_c2(Bm['at'], pre + [None] + post, rel=[(len(pre), at['cyc'])])
        # menú HOME (y aviso de salir de MP1, CQuitScreen::ProcessUserInput): mientras corre, tabla de menús
        for hk in ('hbm', 'quit'):
            if hk not in G: continue
            ha, horig = G[hk]
            B.add_c2(ha, words(f"  lis 12,0x{VAR >> 16:x}\n  li 0,{CNT}\n  stw 0,{V + V_HBMC}(12)\n  {horig}\n"))
        B.L.append("E0000000 80008000")
        sizes[g] = (len(B.L) - n0) * 8
    codes = b''.join(bytes.fromhex(l.replace(' ', '')) for l in B.L)
    return B.L, codes, at, sizes

def final():
    """Lo que va en el .gct: la lista tal cual o un C0 con el descompresor y la lista comprimida.
    Devuelve (lista en texto, códigos del .gct, offsets del C0 común, tamaños, info de la compresión)."""
    L, codes, at, sizes = build()
    if not COMPRESS: return L, codes, at, sizes, None
    import build_gct as BG, unpack_asm as UA
    payload = codes + b''.join(bytes.fromhex(l.replace(' ', '')) for l in UA.ret_c0_lines(BG.RET))
    assert BG.LIST + len(payload) <= VAR, 'la lista descomprimida pisaría las variables'
    used = [v for k, v in globals().items() if k.startswith('V_') and isinstance(v, int) and True]
    assert max(used) + 4 <= BG.PROBS - VAR, 'las variables pisarían la tabla de probabilidades'
    c0, info = BG.build(payload)
    info['lista'] = len(payload)
    return L, c0, at, sizes, info

def write_outputs(outdir):
    L, codes, at, sizes, info = final()
    gct = bytes.fromhex('00D0C0DE00D0C0DE') + codes + bytes.fromhex('F000000000000000')
    name = f"Classic Controller {VERSION}"
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, 'R3MP01.gct'), 'wb').write(gct)
    CL_ = ['%s %s' % (codes[i:i + 4].hex().upper(), codes[i + 4:i + 8].hex().upper()) for i in range(0, len(codes), 8)]
    if info: open(os.path.join(outdir, f'lista-{VERSION}.txt'), 'w', newline='\r\n').write('\n'.join(L) + '\n')
    L = CL_
    ini = ['[Gecko]', '$' + name] + L + ['', '[Gecko_Enabled]', '$' + name, '']
    open(os.path.join(outdir, 'R3MP01.ini'), 'w', newline='\r\n').write('\n'.join(ini))
    open(os.path.join(outdir, f'gecko-{VERSION}.txt'), 'w', newline='\r\n').write('$' + name + '\n' + '\n'.join(L) + '\n')
    # formato del gestor de trucos de USB Loader GX (sd:/txtcodes/R3MP01.txt)
    txt = ['R3MP01', 'Metroid Prime Trilogy', '', name] + L + ['']
    open(os.path.join(outdir, 'R3MP01.txt'), 'w', newline='\r\n').write('\n'.join(txt) + '\n')
    return L, gct, at, sizes, info

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    L, gct, at, sizes, info = write_outputs(out)
    print('tamaños por bloque, sin comprimir (bytes):', sizes, 'total', sum(sizes.values()))
    if info: print('comprimido:', info)
    print('GCT', len(gct), 'bytes de', LIMIT, '->', 'OK' if len(gct) <= LIMIT else 'DEMASIADO GRANDE', f'(libres: {LIMIT - len(gct)})')
