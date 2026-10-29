"""Pruebas de la rama nueva (bloque base) en el emulador (Unicorn + codehandler de Dolphin + los 4 .dol de Trilogy).
Uso: python pruebas_base.py   (EMU = carpeta con emu.py; por defecto tests/emu)"""
import sys, os, math, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
# emulador (emu.py, codehandler.bin) de la rama unificada; con EMU se puede indicar otra carpeta
sys.path.insert(0, os.environ.get('EMU', os.path.join(HERE, 'emu')))
import base as BS
from emu import Machine, install_timebase, dolimage
from unicorn import UC_HOOK_CODE

L, CODES, AT, SIZES, INFO = BS.final()     # n0.6: CODES = C0 con la lista comprimida (NOCOMP=1: sin comprimir)
UNC = BS.build()[1]                          # la lista sin comprimir
LIST = 0x80004180 if INFO else 0x80002340   # dónde se ejecuta la lista
VAR = BS.VAR; KP = 0x81100000; R28 = 0x81101000; PL = 0x81300000; SMO = 0x81200000; CB = 0x81500000; CUR = 0x81510000
CTL = 0x81600000; ARM = 0x81700000
CL, WM = BS.CL, BS.WM
fails = []; covered = set()
def check(cond, msg):
    print(('OK    ' if cond else 'FALLO ') + msg)
    if not cond: fails.append(msg)

def machine(g, prefix=b''):
    m = Machine(g); m.install(prefix + CODES)
    sh = 0 if INFO else len(prefix)
    lo = LIST + sh
    m.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: covered.add(a - sh), begin=lo, end=lo + len(UNC))
    m.run_codehandler(50_000_000); m.run_codehandler(50_000_000)
    return m
G = BS.GAMES
def F(g, k): return G[g]['f'].get(k, 0)
def classic(m, held=0, trig=0, rel=0, ls=(0, 0), rs=(0, 0), dev=2, wm=0):
    m.uc.mem_write(KP, b'\0' * 0xb0)
    m.w32(KP, wm); m.w8(KP + 0x5c, dev); m.w32(KP + 0x60, held); m.w32(KP + 0x64, trig); m.w32(KP + 0x68, rel)
    m.wf(KP + 0x6c, ls[0]); m.wf(KP + 0x70, ls[1]); m.wf(KP + 0x74, rs[0]); m.wf(KP + 0x78, rs[1])
    m.wf(KP + 0xc, 0.1); m.wf(KP + 0x10, -0.9); m.wf(KP + 0x14, 0.2); m.wf(KP + 0x18, 1.0)
def kpad(m, g):
    m.call_hook(G[g]['khook'], regs={G[g]['kreg']: KP, 28: R28, 24: R28})
def press(m, g, btn, **kw):
    classic(m, held=btn, trig=btn, **kw); kpad(m, g); return m.r32(KP) & 0xffff

def setxf(m, base, a=0.3):
    M = [math.cos(a), -math.sin(a), 0, 10.0, math.sin(a), math.cos(a), 0, -5.0, 0, 0, 1, 2.0]
    for j, v in enumerate(M): m.wf(base + 4 * j, v)
def ingame(m, g, ball=0, menu=0, lock=0, orb=0, ctl=1, move=0, hand=0):
    """estado de juego falso: jugador en PL (hand = MP3 en una sección con la mano: orden 0 desactivada)"""
    m.w32(PL, 0x80400000)                                   # vtable del jugador (MP1/MP2 leen aquí con abil = 0)
    if F(g, 'abil'): m.w8(PL + F(g, 'abil'), 0 if hand else 1)
    if g == 'MP3':
        m.w32(F(g, 'pl1'), SMO); m.w32(SMO + F(g, 'pl2'), PL)
        m.w32(PL + F(g, 'ctl'), CTL if ctl is not None else 0); m.w32(CTL + 0x7cc, ctl or 0)
    else:
        m.w32(F(g, 'pl1'), PL)
    if F(g, 'ing'): m.w32(F(g, 'ing'), 1)
    m.w8(F(g, 'menu'), menu); m.w8(F(g, 'lock'), lock)
    m.w32(PL + F(g, 'ball'), ball); m.w32(PL + F(g, 'orb'), orb)
    if F(g, 'move'): m.w32(PL + F(g, 'move'), move)
    m.w32(F(g, 'curb'), CB); m.w32(CB + 0xd04, CUR); m.wf(CUR + 0x9c, 0.7); m.wf(CUR + 0x15c, 0.7)
    if F(g, 'arm1'): m.w32(PL + F(g, 'arm1'), ARM)
    setxf(m, PL + F(g, 'xf')); m.wf(PL + F(g, 'pitch'), 0.0)

ALL = ['MP3', 'MP1', 'MP2']
print('tamaño:', len(CODES) + 16, 'bytes de', BS.LIMIT, SIZES, INFO)
check(len(CODES) + 16 <= BS.LIMIT, f'cabe en Dolphin ({len(CODES) + 16} de {BS.LIMIT} bytes)')

# ---------------------------------------------------------------------------------------------------------------
# parches fijos de cada juego (y nada en los otros)
for g in ALL + ['FE']:
    m = machine(g)
    ok = m.r32(G[g]['ext']) == 0x4182003C
    for a, v in BS.CAM.get(g, []): ok &= m.r32(a) == v
    if 'spring' in G[g]: ok &= m.r32(G[g]['spring']) == 0x3C608000 and m.r32(G[g]['spring'] + 4) == 0x88635984
    if 'skip' in G[g]: ok &= m.r32(G[g]['skip'][0]) == 0x38600001 and m.r32(G[g]['skip'][0] + 4) == 0x4E800020
    check(ok, f'{g}: parches fijos escritos (Nunchuk, cámara, bola muelle, cinemáticas vistas)')
    d = dolimage(g); others = [h for h in ALL + ['FE'] if h != g]
    bad = [h for h in others if G[h]['ext'] != G[g]['ext'] and d.u32(G[h]['ext']) is not None and m.r32(G[h]['ext']) != d.u32(G[h]['ext'])]
    check(not bad, f'{g}: no se aplican los parches de los otros juegos {bad}')

# ---------------------------------------------------------------------------------------------------------------
# menús
MENU_MAP = [('A', 'A'), ('R', None), ('B', 'B'), ('ZL', None), ('UP', 'UP'), ('DOWN', 'DOWN'), ('LEFT', 'LEFT'),
            ('RIGHT', 'RIGHT'), ('MINUS', '1'), ('HOME', 'HOME'), ('L', None), ('ZR', None), ('Y', None), ('X', None)]
for g in ALL + ['FE']:
    m = machine(g)
    if g != 'FE': ingame(m, g, menu=(4 if g != 'MP3' else 1))   # MP1/MP2: 1 = mapa, 2/3 = pausa; 4 = otro menú
    pb = F(g, 'pbtn')
    res = [(c, press(m, g, CL[c]), WM[w] if w else 0) for c, w in MENU_MAP + [('PLUS', None)]]
    res[-1] = ('PLUS', res[-1][1], pb)
    bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
    check(not bad, f'{g}: menú: solo A = A y solo B = B (R y ZL nada), cruceta, − = 1, + = {pb:#x}, HOME; L/ZR/Y/X nada {bad}')
    classic(m); kpad(m, g)
    xs = []
    for i in range(60):
        classic(m, ls=(1.0, 0.0), rs=(0.0, 1.0)); kpad(m, g); xs.append((m.rf(KP + 0x20), m.rf(KP + 0x24)))
    check(all(b[0] >= a[0] for a, b in zip(xs, xs[1:])) and abs(xs[-1][0] - 0.8) < 1e-6 and xs[-1][1] == xs[0][1],
          f'{g}: menú: el stick izq. mueve el puntero (con aceleración, tope 0,8) y el derecho no hace nada')
    ny = m.rf(KP + 0x64); nx = m.rf(KP + 0x60)
    check(m.r8(KP + 0x5c) == 1 and m.r8(KP + 0x5e) == 2 and nx == 1.0 and ny == 0.0, f'{g}: menú: Nunchuk emulado (stick izq.) y puntero válido')
    for i in range(3): classic(m); kpad(m, g)
    x1 = m.rf(KP + 0x20)
    check(abs(x1 - 0.8) < 1e-6, f'{g}: menú: al soltar el stick el puntero se queda donde estaba')
    if g != 'FE':
        xf0 = m.rd(PL + F(g, 'xf'), 48)
        classic(m, rs=(1.0, 1.0)); kpad(m, g)
        check(m.rd(PL + F(g, 'xf'), 48) == xf0, f'{g}: menú: la cámara no se mueve')

# MP2: en carga (SM+0x153C != 1) también es menú
m = machine('MP2'); ingame(m, 'MP2'); m.w32(F('MP2', 'ing'), 0)
check(press(m, 'MP2', CL['UP']) == WM['UP'], 'MP2: en carga (estado != 1): tabla de menús')
# MP3 sin jugador: menú
m = machine('MP3'); m.w32(F('MP3', 'pl1'), 0)
check(press(m, 'MP3', CL['DOWN']) == WM['DOWN'], 'MP3: sin jugador: tabla de menús')

# ---------------------------------------------------------------------------------------------------------------
# jugando
# n0.4: cruceta arriba = − del Wiimote (ruleta de visores), abajo = + (ruleta de rayos, solo MP1/MP2)
GAME_MAP = [('A', 'A'), ('R', 'A'), ('B', 'B'), ('ZL', 'B'), ('L', 'Z'), ('ZR', 'DOWN'), ('Y', 'C'), ('MINUS', '1'),
            ('HOME', 'HOME'), ('UP', 'MINUS' if BS.WHEEL else None), ('DOWN', 'PLUS' if BS.WHEEL else None),
            ('LEFT', None), ('RIGHT', None), ('X', None)]
def gexp(g, c, w):
    if c == 'DOWN' and g == 'MP3': return WM['2']   # n0.10: MP3: cruceta abajo = pista (2 del Wiimote)
    return WM[w] if w else 0
for g in ALL:
    m = machine(g); ingame(m, g)
    res = [(c, press(m, g, CL[c]), gexp(g, c, w)) for c, w in GAME_MAP] + [('PLUS', press(m, g, CL['PLUS']), F(g, 'pbtn'))]
    bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
    check(not bad, f'{g}: jugando: A/R disparar, B/ZL saltar, L fijar, ZR misil, Y morfosfera, − = 1, + = {F(g, "pbtn"):#x}, '
          f'cruceta arriba = − (visores)' + ('' if g == 'MP3' else ', abajo = + (rayos)') + f'; el resto de la cruceta y X nada {bad}')
    classic(m, held=CL['A'] | CL['L'], trig=CL['A'], rel=CL['ZR']); m.w32(KP, WM['2']); m.w32(KP + 4, 0); m.w32(KP + 8, 0); kpad(m, g)
    check(m.r32(KP) == WM['A'] | WM['Z'] | WM['2'] and m.r32(KP + 4) == WM['A'] and m.r32(KP + 8) == WM['DOWN'],
          f'{g}: jugando: pulsado / recién pulsado / soltado por separado, y los botones del Wiimote siguen valiendo')
    # cámara
    xf = PL + F(g, 'xf'); p0 = m.rf(PL + F(g, 'pitch'))
    a0 = math.atan2(m.rf(xf + 16), m.rf(xf))
    classic(m, ls=(0.3, -0.4), rs=(1.0, 1.0)); kpad(m, g)
    a1 = math.atan2(m.rf(xf + 16), m.rf(xf)); p1 = m.rf(PL + F(g, 'pitch'))
    check(abs((a0 - a1) - BS.YAW_RATE) < 1e-3 and abs(p1 - p0 - BS.PITCH_RATE) < 1e-6,
          f'{g}: stick der. a la derecha gira la cámara {math.degrees(a0 - a1):.2f}° y arriba sube {p1 - p0:.3f}')
    check(abs(m.rf(KP + 0x60) - 0.3) < 1e-6 and abs(m.rf(KP + 0x64) + 0.4) < 1e-6, f'{g}: stick izq. = stick del Nunchuk')
    check(m.rf(KP + 0x20) == 0 and abs(m.rf(KP + 0x24)) == 0 and m.rf(CUR + 0x9c) == 0 and abs(m.rf(CUR + 0x15c)) == 0,
          f'{g}: mira centrada (puntero y cursor del juego en 0)')
    angk = struct.unpack('>f', struct.pack('>I', BS.f2u(dict(BS.K)['TINY' if g == 'MP3' else 'ZERO'])))[0]
    check(m.rf(PL + F(g, 'angmom')) == angk and m.rf(PL + F(g, 'angvel')) == angk, f'{g}: velocidad de giro del juego anulada')
    if g == 'MP1': check(abs(m.rf(F(g, 'arms')) - p1) < 1e-6, 'MP1: el arma sigue el pitch')
    if g == 'MP2': check(abs(m.rf(ARM + F(g, 'arm2')) - p1) < 1e-6, 'MP2: el arma sigue el pitch')
    for i in range(60): classic(m, rs=(0, 1.0)); kpad(m, g)
    check(abs(m.rf(PL + F(g, 'pitch')) - BS.PITCH_MAX) < 1e-6, f'{g}: el pitch se para en {BS.PITCH_MAX}')
    classic(m, rs=(0.1, -0.1)); xf0 = m.rd(xf, 48); kpad(m, g)
    check(m.rd(xf, 48) == xf0, f'{g}: zona muerta del stick derecho')
    # fijado
    ingame(m, g, lock=1); xf0 = m.rd(xf, 48); classic(m, rs=(1.0, 0)); kpad(m, g)
    check(m.rd(xf, 48) == xf0 and m.rf(KP + 0x20) == 0, f'{g}: con blanco fijado no se mueve la cámara')
    ov = F(g, 'orbv')
    ingame(m, g, lock=1, orb=ov); xf0 = m.rd(xf, 48); classic(m, rs=(1.0, 0)); kpad(m, g)
    check(m.rd(xf, 48) != xf0, f'{g}: fijado con gancho/látigo (órbita {ov}): cámara libre')
    if g == 'MP3':
        ingame(m, g, orb=1); xf0 = m.rd(xf, 48); classic(m, rs=(1.0, 0)); kpad(m, g)
        check(m.rd(xf, 48) == xf0, 'MP3: órbita 1 sin cámara (como la v1.1)')
        ingame(m, g, ctl=2); classic(m); kpad(m, g); x0 = m.rf(KP + 0x20)
        for i in range(10): classic(m, ls=(1.0, 0), rs=(1.0, 0)); kpad(m, g)
        check(m.rf(KP + 0x20) > x0 + 0.05 and press(m, g, CL['L']) == WM['Z'],
              'MP3: estado de control != 1: el stick izq. mueve el puntero, con los botones de jugar')
        ingame(m, g, ctl=None); xf0 = m.rd(xf, 48); classic(m, rs=(1.0, 0)); kpad(m, g)
        check(m.rd(xf, 48) == xf0, 'MP3: sin estado de control: sin cámara')
    # morfosfera
    ingame(m, g, ball=1)
    res = [(c, press(m, g, CL[c]), gexp(g, c, w)) for c, w in GAME_MAP if c != 'X']
    bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
    check(not bad, f'{g}: morfosfera: A/R bomba, B/ZL impulso (B), L aracnosfera (Z), ZR bomba de energía, Y salir {bad}')
    xf0 = m.rd(xf, 48); classic(m, rs=(1.0, 1.0)); kpad(m, g)
    check(m.rd(xf, 48) == xf0, f'{g}: morfosfera: el stick der. no gira a Samus')
    seq = []
    for i in range(10):
        classic(m, held=CL['X'], trig=CL['X'] if i == 0 else 0); kpad(m, g); seq.append(m.r8(VAR + 0x84))
    check(seq == [1] * BS.SPRING_FRAMES + [0] * (10 - BS.SPRING_FRAMES), f'{g}: X = una sola sacudida aunque se mantenga {seq}')
    classic(m); kpad(m, g)
    check(press(m, g, CL['X']) == 0 and m.r8(VAR + 0x84) == 1, f'{g}: X otra vez = otra sacudida, sin botón del Wiimote')
    if F(g, 'move'):
        for i in range(6): classic(m); kpad(m, g)
        ingame(m, g, ball=1, move=1); press(m, g, CL['X'])
        check(m.r8(VAR + 0x84) == 0, f'{g}: bola muelle solo en el suelo (como PrimeHack)')
    ingame(m, g); press(m, g, CL['X'])
    check(m.r8(VAR + 0x84) == 0, f'{g}: fuera de la morfosfera X no hace nada')

# ---------------------------------------------------------------------------------------------------------------
# HOME de la Wii
for g in ALL + ['FE']:
    m = machine(g)
    if g != 'FE': ingame(m, g)
    a, orig = G[g]['hbm']; reg = int(orig.split('(')[1].rstrip(')'))
    m.call_hook(a, regs={reg: 0x81750000})
    check(m.r32(VAR + BS.V_HBMC) == 12, f'{g}: el gancho del menú HOME avisa al núcleo')
    if g != 'FE': ingame(m, g)
    def hpress(c): m.call_hook(a, regs={reg: 0x81750000}); return press(m, g, CL[c])
    res = [(c, hpress(c), WM[w] if w else 0) for c, w in MENU_MAP]
    bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
    check(not bad, f'{g}: menú HOME: los botones van como en los menús (A, B, HOME para cerrarlo; R y ZL nada) {bad}')
    m.call_hook(a, regs={reg: 0x81750000}); classic(m); kpad(m, g); x0 = m.rf(KP + 0x20)
    for i in range(20):
        m.call_hook(a, regs={reg: 0x81750000}); classic(m, ls=(-1.0, 0), rs=(1.0, 1.0)); kpad(m, g)
    check(m.rf(KP + 0x20) < x0 - 0.1 and m.r8(KP + 0x5e) == 2, f'{g}: menú HOME: el stick izq. mueve el puntero')
    if g != 'FE':
        xf0 = m.rd(PL + F(g, 'xf'), 48); m.call_hook(a, regs={reg: 0x81750000}); classic(m, rs=(1.0, 1.0)); kpad(m, g)
        check(m.rd(PL + F(g, 'xf'), 48) == xf0, f'{g}: menú HOME: la cámara no se mueve')
        for i in range(13): classic(m); kpad(m, g)
        classic(m, rs=(1.0, 0)); xf0 = m.rd(PL + F(g, 'xf'), 48); kpad(m, g)
        check(m.rd(PL + F(g, 'xf'), 48) != xf0, f'{g}: al cerrar el menú HOME vuelven los controles de jugar')
    m.call_hook(a, regs={reg: 0x81750000}); classic(m, dev=1, wm=WM['A']); kpad(m, g)
    check(m.r8(KP + 0x5c) == 1 and m.r32(KP) == WM['A'], f'{g}: menú HOME con Wiimote + Nunchuk: no se toca')

# ---------------------------------------------------------------------------------------------------------------
# cinemáticas
FRAME_TB = BS.TB // 60
for g in ALL:
    seen, hook, orig = G[g]['skip']; pb = F(g, 'pbtn')
    m = machine(g); install_timebase(m, [(0x80002340, 0x80003000), (0x80004180, 0x80005900)]); ingame(m, g)
    m.w32(orig, 0x3C608160); m.w32(orig + 4, 0x80630000); m.w32(orig + 8, 0x4e800020); m.w32(0x81600000, 0)
    def frame(held, trig=0):
        m.tb += FRAME_TB
        m.call_hook(hook, regs={3: 0x81500000, 4: 4, 5: 0x53}); r = m.reg(3)
        classic(m, held=held, trig=trig); kpad(m, g); outs.append(m.r32(KP) & pb)
        return r
    outs = []
    frame(0)
    check(m.r32(VAR + BS.V_CUTC) == 11, f'{g}: la consulta de saltar marca "en cinemática"')
    rs = [frame(CL['PLUS'], CL['PLUS'] if i == 0 else 0) for i in range(70)]
    first = rs.index(1) if 1 in rs else None
    check(first in (60, 61) and not any(rs[:first]) and all(rs[first:]), f'{g}: mantener + salta al cabo de 1 s (frame {first})')
    check(not any(outs), f'{g}: en cinemática el + no manda nada al juego')
    rs2 = [frame(0), frame(0)] + [frame(CL['PLUS'], CL['PLUS'] if i == 0 else 0) for i in range(30)]
    check(not any(rs2[1:]), f'{g}: al soltar + el contador vuelve a empezar')
    m.w32(0x81600000, 1)
    check(frame(0) == 1, f'{g}: el botón de saltar del propio juego sigue valiendo')
    m.w32(0x81600000, 0)
    # se salta con + mantenido; acaba la cinemática y se sigue manteniendo: no cuenta hasta soltar
    for i in range(65): frame(CL['PLUS'], CL['PLUS'] if i == 0 else 0)
    outs = []
    for i in range(30): classic(m, held=CL['PLUS']); kpad(m, g); outs.append(m.r32(KP) & pb)
    classic(m, rel=CL['PLUS']); kpad(m, g); outs.append(m.r32(KP + 8) & pb)
    check(not any(outs), f'{g}: tras la cinemática, el + que sigue pulsado no cuenta (ni al soltarlo)')
    check(press(m, g, CL['PLUS']) == pb, f'{g}: después, pulsar + vuelve a funcionar al instante')
    # con el Wiimote solo (sin clásico) también vale mantener +
    m.w32(VAR + 0x24, 0)
    classic(m, dev=1, wm=WM['PLUS']); kpad(m, g)
    rs = []
    for i in range(70):
        m.tb += FRAME_TB; m.call_hook(hook, regs={3: 0x81500000}); rs.append(m.reg(3))
        classic(m, dev=1, wm=WM['PLUS']); kpad(m, g)
    check(1 in rs and m.r8(KP + 0x5c) == 1 and m.r32(KP) == WM['PLUS'], f'{g}: con Wiimote + Nunchuk: mantener + salta y el mando no se toca')

# ---------------------------------------------------------------------------------------------------------------
# n0.3: pausa de MP1 (byte de menú 2): cruceta izq./der. = − / + del Wiimote (opciones / banco de datos)
PAUSE_MAP = [('LEFT', 'MINUS'), ('RIGHT', 'PLUS'), ('UP', 'UP'), ('DOWN', 'DOWN'), ('A', 'A'), ('B', 'B'), ('R', None),
             ('ZL', None), ('MINUS', '1'), ('HOME', 'HOME'), ('L', None), ('ZR', None), ('Y', None), ('X', None)]
m = machine('MP1'); ingame(m, 'MP1', menu=2)
res = [(c, press(m, 'MP1', CL[c]), WM[w] if w else 0) for c, w in PAUSE_MAP] + [('PLUS', press(m, 'MP1', CL['PLUS']), WM['2'])]
bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
check(not bad, f'MP1: pausa: cruceta izq. = − (opciones), der. = + (banco de datos), arriba/abajo normales, A, B {bad}')
classic(m, held=CL['LEFT'], trig=0, rel=CL['RIGHT']); kpad(m, 'MP1')
check(m.r32(KP) == WM['MINUS'] and m.r32(KP + 4) == 0 and m.r32(KP + 8) == WM['PLUS'], 'MP1: pausa: mantenido y soltado por separado')
for g, v in [('MP3', 2)]:
    m = machine(g); ingame(m, g, menu=v)
    check(press(m, g, CL['LEFT']) == WM['LEFT'] and press(m, g, CL['RIGHT']) == WM['RIGHT'],
          f'{g}: con el byte de menú en {v} la cruceta izq./der. sigue siendo cruceta (lo de la pausa es solo de MP1)')

# ---------------------------------------------------------------------------------------------------------------
# n0.3: mapa (MP1/MP2: byte de menú 1; MP3 todavía no: se hará como en el port)
MAPV_MAP = [('UP', 'PLUS'), ('DOWN', 'MINUS'), ('LEFT', 'LEFT'), ('RIGHT', 'RIGHT'), ('L', 'Z'), ('A', 'A'), ('B', 'B'),
            ('R', None), ('ZL', None), ('MINUS', '1'), ('HOME', 'HOME'), ('ZR', None), ('Y', 'C'), ('X', None)]
MH, MORIG = BS.MP3_MAP_HOOK
def mapopen(m, g):
    if g == 'MP3': m.call_hook(MH, regs={29: 0x81760000, 31: 0x81760000, 4: 1})
MAPG = [('MP1', 1), ('MP2', 1), ('MP2', 3), ('MP2', 2)] + ([('MP3', 0)] if BS.MAP_MP3 else [])
for g, mv in MAPG:
    m = machine(g); ingame(m, g, menu=mv); print('   (byte de menú', mv, ')')
    if g == 'MP3':
        m.w32(0x81760000 + 0x7bc, 0x81234560)
        m.call_hook(MH, regs={29: 0x81760000, 31: 0x81760000, 4: 1})
        check(m.r32(VAR + BS.V_MAPC) == BS.MAPCNT and m.reg(3) == 0x81234560,
              f'MP3: el C2 del mapa avisa al núcleo ({BS.MAPCNT} frames) y hace la instrucción original ({MORIG})')
    def mpress(c): mapopen(m, g); return press(m, g, CL[c])
    res = [(c, mpress(c), WM[w] if w else 0) for c, w in MAPV_MAP] + [('PLUS', mpress('PLUS'), F(g, 'pbtn'))]
    bad = [(c, hex(got), hex(exp)) for c, got, exp in res if got != exp]
    check(not bad, f'{g}: mapa: cruceta arriba = + (zoom +), abajo = − (zoom −), L = Z, A, B; R y ZL nada {bad}')
    mapopen(m, g); classic(m, held=CL['UP'] | CL['L'], trig=CL['UP'], rel=CL['DOWN']); kpad(m, g)
    check(m.r32(KP) == WM['PLUS'] | WM['Z'] and m.r32(KP + 4) == WM['PLUS'] and m.r32(KP + 8) == WM['MINUS'],
          f'{g}: mapa: zoom mantenido / recién pulsado / soltado por separado')
    mapopen(m, g); classic(m); kpad(m, g); x0 = m.rf(KP + 0x20); xf0 = m.rd(PL + F(g, 'xf'), 48)
    for i in range(10): mapopen(m, g); classic(m, ls=(1.0, 0.0), rs=(-0.6, 0.8)); kpad(m, g)
    rsm = BS.MAP_RS and g == 'MP3'   # n0.7: solo el mapa de MP3 gira con el stick der.
    nx, ny = (-0.6, 0.8) if rsm else (1.0, 0.0)
    check(abs(m.rf(KP + 0x60) - nx) < 1e-6 and abs(m.rf(KP + 0x64) - ny) < 1e-6 and m.r8(KP + 0x5c) == 1,
          f'{g}: mapa: el stick ' + ('derecho' if rsm else 'izquierdo (como antes)') + ' es el stick del Nunchuk (girar; con L, mover)')
    if rsm:
        mapopen(m, g); classic(m, held=CL['L'], ls=(0.5, 0.5), rs=(0.3, -0.7)); kpad(m, g)
        check(m.r32(KP) & WM['Z'] and abs(m.rf(KP + 0x60) - 0.3) < 1e-6 and abs(m.rf(KP + 0x64) + 0.7) < 1e-6,
              'MP3: mapa: L + stick der. = Z + stick del Nunchuk (desplazar), el izquierdo no llega al Nunchuk')
    check(m.rf(KP + 0x20) > x0 + 0.05 and m.r8(KP + 0x5e) == 2, f'{g}: mapa: el stick izq. sigue moviendo el puntero')
    check(m.rd(PL + F(g, 'xf'), 48) == xf0, f'{g}: mapa: la cámara no se mueve')
    # al cerrar el mapa: vuelven los controles de jugar
    if g == 'MP3':
        for i in range(BS.MAPCNT): classic(m); kpad(m, g)
    else:
        ingame(m, g)
    classic(m, ls=(0.3, -0.4), rs=(1.0, 0)); xf0 = m.rd(PL + F(g, 'xf'), 48); kpad(m, g)
    check(m.rd(PL + F(g, 'xf'), 48) != xf0 and abs(m.rf(KP + 0x60) - 0.3) < 1e-6
          and press(m, g, CL['UP']) == (WM['MINUS'] if BS.WHEEL else 0)
          and press(m, g, CL['R']) == WM['A'], f'{g}: al cerrar el mapa vuelven los controles de jugar')
if BS.MAP_MP3:
    # MP3: el aviso del mapa gana aunque el byte de menú (cursor) esté puesto; el menú HOME gana al mapa
    m = machine('MP3'); ingame(m, 'MP3', menu=1); mapopen(m, 'MP3')
    check(press(m, 'MP3', CL['DOWN']) == WM['MINUS'], 'MP3: mapa con el byte de menú puesto: sigue siendo mapa')
    a, orig = G['MP3']['hbm']; reg = int(orig.split('(')[1].rstrip(')'))
    mapopen(m, 'MP3'); m.call_hook(a, regs={reg: 0x81750000})
    check(press(m, 'MP3', CL['DOWN']) == WM['DOWN'], 'MP3: menú HOME encima del mapa: tabla de menús')
else:
    m = machine('MP3'); d = dolimage('MP3'); ingame(m, 'MP3', menu=1)
    check(m.r32(BS.MP3_MAP_HOOK[0]) == d.u32(BS.MP3_MAP_HOOK[0]) and press(m, 'MP3', CL['UP']) == WM['UP'],
          'MP3: sin cambios en el mapa todavía (sin C2; con el byte de menú puesto, tabla de menús)')
m = machine('MP1'); ingame(m, 'MP1', menu=1); m.call_hook(G['MP1']['hbm'][0], regs={30: 0x81750000})
check(press(m, 'MP1', CL['UP']) == WM['UP'], 'MP1: menú HOME encima del mapa: tabla de menús')

# ---------------------------------------------------------------------------------------------------------------
# n0.4: ruletas (visores: cruceta arriba, los tres juegos; rayos: cruceta abajo, MP1/MP2)
if BS.WHEEL:
    WSX, WSY, WTY = BS.WHEEL_SIDE_X, BS.WHEEL_SIDE_Y, BS.WHEEL_TOP_Y
    def near(a, b): return abs(a - b) < 1e-6
    def ptr(m): return (m.rf(KP + 0x20), m.rf(KP + 0x24))
    def at(m, x, y):    # puntero y cursor del juego en la opción (x, y) (coordenadas del stick, y+ = arriba)
        return near(m.rf(KP + 0x20), x) and near(m.rf(KP + 0x24), -y) and near(m.rf(CUR + 0x9c), x) and near(m.rf(CUR + 0x15c), -y)
    CASES = [((0, 1.0), (0, WTY)), ((1.0, -0.2), (WSX, WSY)), ((-1.0, -0.2), (-WSX, WSY)), ((0.3, -1.0), (WSX, WSY)),
             ((-0.3, -1.0), (-WSX, WSY)), ((1.0, 0.45), (WSX, WSY)), ((1.0, 0.55), (0, WTY)), ((-0.8, 0.8), (0, WTY)),
             ((-1.0, 0.45), (-WSX, WSY)), ((0.75, 0.0), (WSX, WSY))]
    for g in ALL:
        xf = PL + F(g, 'xf'); pa = PL + F(g, 'pitch')
        for c, w, name in [('UP', 'MINUS', 'visores')] + ([('DOWN', 'PLUS', 'rayos')] if g != 'MP3' else []):
            m = machine(g); ingame(m, g); classic(m); kpad(m, g); b = CL[c]
            xf0 = m.rd(xf, 48); p0 = m.rf(pa); m.wf(PL + F(g, 'angmom'), 0.5)
            classic(m, held=b, trig=b, rs=(0.5, 0.3)); kpad(m, g)
            check(m.r32(KP) & 0xffff == WM[w] and at(m, 0, 0) and m.rd(xf, 48) == xf0 and m.rf(pa) == p0,
                  f'{g}: ruleta de {name} (cruceta {c}): manda {w} del Wiimote, puntero en el centro y la cámara quieta')
            bad = []
            for st, (ex, ey) in CASES:
                classic(m, held=b, rs=st); kpad(m, g)
                if not at(m, ex, ey): bad.append((st, ptr(m)))
            check(not bad and m.rd(xf, 48) == xf0 and m.rf(pa) == p0,
                  f'{g}: ruleta de {name}: el stick der. pega el puntero a la opción hacia la que apunta (arriba o su lado) {bad}')
            classic(m, held=b, rs=(-1.0, -0.2)); kpad(m, g)
            ok = True
            for st in [(-0.6, -0.1), (-0.2, 0), (0, 0), (0.3, 0.3), (0, 0)]:
                classic(m, held=b, rs=st); kpad(m, g); ok &= at(m, -WSX, WSY)
            check(ok, f'{g}: ruleta de {name}: al soltar el stick (o moverlo poco) el puntero se queda en la opción')
            # n0.7: tras WHEEL_CENTER_FRAMES sin tocarlo vuelve al centro (y moverlo reinicia la cuenta)
            WF = BS.WHEEL_CENTER_FRAMES; seq = []
            classic(m, held=b, rs=(-1.0, -0.2)); kpad(m, g)
            for i in range(WF - 1): classic(m, held=b, rs=(0.2, 0)); kpad(m, g)
            seq.append(at(m, -WSX, WSY))
            classic(m, held=b, rs=(-1.0, -0.2)); kpad(m, g)
            for i in range(WF - 1): classic(m, held=b); kpad(m, g)
            seq.append(at(m, -WSX, WSY))
            classic(m, held=b); kpad(m, g); seq.append(at(m, 0, 0))
            for i in range(5): classic(m, held=b); kpad(m, g)
            seq.append(at(m, 0, 0) and m.rd(xf, 48) == xf0)
            classic(m, held=b, rs=(-1.0, -0.2)); kpad(m, g); seq.append(at(m, -WSX, WSY))
            check(seq == [True] * 5, f'{g}: ruleta de {name}: tras {WF} frames ({WF / 60:g} s) sin tocar el stick der. el puntero vuelve al centro; moverlo reinicia la cuenta {seq}')
            classic(m, rel=b); kpad(m, g)
            check(at(m, -WSX, WSY) and m.r32(KP + 8) & 0xffff == WM[w] and m.r32(KP) & 0xffff == 0 and m.rd(xf, 48) == xf0,
                  f'{g}: ruleta de {name}: el frame en que se suelta la cruceta (cuando el juego elige) el puntero sigue en la opción')
            classic(m, rs=(1.0, 0)); kpad(m, g)
            check(m.rd(xf, 48) != xf0 and at(m, 0, 0), f'{g}: ruleta de {name}: después vuelven la cámara y la mira centrada')
            classic(m, held=b, trig=b); kpad(m, g)
            check(at(m, 0, 0), f'{g}: ruleta de {name}: al volver a abrirla empieza en el centro (visor/rayo normal)')
        m = machine(g); ingame(m, g, lock=1); classic(m); kpad(m, g)
        classic(m, held=CL['UP'], trig=CL['UP'], rs=(0, 1.0)); kpad(m, g)
        check(at(m, 0, WTY), f'{g}: con blanco fijado la ruleta también va')
        m = machine(g); ingame(m, g, ball=1); classic(m); kpad(m, g)
        classic(m, held=CL['UP'], trig=CL['UP'], rs=(0, 1.0)); kpad(m, g)
        check(at(m, 0, 0), f'{g}: en morfosfera la cruceta arriba no mueve el puntero')
        if g == 'MP3':
            m = machine(g); ingame(m, g); classic(m); kpad(m, g); xf0 = m.rd(xf, 48)
            classic(m, held=CL['DOWN'], trig=CL['DOWN'], rs=(1.0, 0)); kpad(m, g)
            check(m.r32(KP) & 0xffff == WM['2'] and m.rd(xf, 48) != xf0, 'MP3: cruceta abajo = pista (2 del Wiimote), sin ruleta, y la cámara sigue')
    # cambiar de juego: la entrada de la cruceta abajo se rehace con el juego que está cargado
    m = machine('MP1'); ingame(m, 'MP1'); ok1 = press(m, 'MP1', CL['DOWN']) == WM['PLUS']
    m2 = machine('MP3'); ingame(m2, 'MP3'); ok3 = press(m2, 'MP3', CL['DOWN']) == WM['2']
    check(ok1 and ok3, 'cruceta abajo: + del Wiimote en MP1, 2 (pista) en MP3 (sale del botón de pausa de cada juego)')

# ---------------------------------------------------------------------------------------------------------------
# n0.5: MP3, secciones con la mano (orden 0 desactivada): stick izq. = mano (relativo, con límites), stick der. = cámara
if BS.HAND:
    HX, HY = BS.INT_LIM_X, BS.INT_LIM_Y
    def near(a, b): return abs(a - b) < 1e-5
    def hand_at(m, x, y):
        return near(m.rf(KP + 0x20), x) and near(m.rf(KP + 0x24), -y) and near(m.rf(CUR + 0x9c), x) and near(m.rf(CUR + 0x15c), -y)
    def hp(m): return (round(m.rf(KP + 0x20), 4), round(m.rf(KP + 0x24), 4))
    g = 'MP3'; xf = PL + F(g, 'xf'); pa = PL + F(g, 'pitch')
    m = machine(g); ingame(m, g); classic(m); kpad(m, g)
    ingame(m, g, hand=1)
    classic(m, ls=(1.0, 0)); kpad(m, g)
    check(hand_at(m, BS.INT_SENS, 0), f'MP3: con la mano, el stick izq. mueve la mano poco a poco ({BS.INT_SENS} por frame a tope) {hp(m)}')
    for i in range(5): classic(m, ls=(0.5, 1.0)); kpad(m, g)
    check(hand_at(m, BS.INT_SENS * 3.5, BS.INT_SENS * 5), f'MP3: con la mano: la velocidad va con lo que se empuja el stick {hp(m)}')
    for i in range(3): classic(m); kpad(m, g)
    check(hand_at(m, BS.INT_SENS * 3.5, BS.INT_SENS * 5), f'MP3: con la mano: al soltar el stick la mano se queda donde estaba {hp(m)}')
    h0 = hp(m)
    for st in [(-0.11, 0.0), (0.0, 0.1), (0.08, -0.08), (-0.05, 0.11)]: classic(m, ls=st); kpad(m, g)
    check(hp(m) == h0, f'MP3: con la mano: zona muerta ({BS.AXIS_DZ}): la vuelta del stick al centro no mueve la mano (no rebota) {hp(m)}')
    classic(m, ls=(-0.3, 0.0)); kpad(m, g)
    check(hand_at(m, BS.INT_SENS * (3.5 - 0.3), BS.INT_SENS * 5), f'MP3: con la mano: pasada la zona muerta se mueve con lo que se empuja {hp(m)}')
    xs = []
    for i in range(60): classic(m, ls=(1.0, 1.0)); kpad(m, g); xs.append(m.rf(KP + 0x20))
    p1 = hp(m); ok1 = abs(xs[-1] - HX) < 0.002 and near(m.rf(KP + 0x24), -HY) and max(xs) <= HX + 1e-6
    dx = [b - a for a, b in zip(xs, xs[1:])]
    soft = all(d >= -1e-7 for d in dx) and all(dx[i + 1] <= dx[i] + 1e-7 for i in range(len(dx) - 1) if xs[i] > HX - BS.HAND_SOFT)
    for i in range(80): classic(m, ls=(-1.0, -1.0)); kpad(m, g)
    ok2 = abs(m.rf(KP + 0x20) + HX) < 0.002 and near(m.rf(KP + 0x24), HY) and abs(m.rf(CUR + 0x9c) - m.rf(KP + 0x20)) < 1e-7
    check(ok1 and ok2, f'MP3: con la mano: llega a ±{HX} / ±{HY} (los límites del mod) sin pasarse {p1} {hp(m)}')
    check(soft, f'MP3: con la mano: en los últimos {BS.HAND_SOFT} hacia el tope horizontal frena poco a poco (sin parón de golpe)')
    for i in range(30): classic(m, ls=(1.0, 0.0)); kpad(m, g)
    x0 = m.rf(KP + 0x20); classic(m, ls=(1.0, 0.0)); kpad(m, g)
    check(abs(m.rf(KP + 0x20) - x0 - BS.INT_SENS) < 1e-6 or abs(x0) > HX - BS.HAND_SOFT, 'MP3: con la mano: lejos del tope va a la velocidad normal')
    for i in range(60): classic(m, ls=(1.0, 0.0)); kpad(m, g)
    x0 = m.rf(KP + 0x20); classic(m, ls=(-1.0, 0.0)); kpad(m, g)
    check(abs(x0 - m.rf(KP + 0x20) - BS.INT_SENS) < 1e-6, 'MP3: con la mano: desde el tope, hacia dentro sale a la velocidad normal')
    xf0 = m.rd(xf, 48); p0 = m.rf(pa); h0 = hp(m)
    classic(m, rs=(1.0, 1.0)); kpad(m, g)
    check(m.rd(xf, 48) != xf0 and m.rf(pa) > p0 and hp(m) == h0, 'MP3: con la mano: el stick der. sigue moviendo la cámara (y la mano no se mueve)')
    xf0 = m.rd(xf, 48); classic(m, ls=(0.5, 0.5), rs=(0.1, -0.1)); kpad(m, g)
    check(m.rd(xf, 48) == xf0, 'MP3: con la mano: zona muerta del stick der. igual que jugando')
    check(press(m, g, CL['A']) == WM['A'] and press(m, g, CL['L']) == WM['Z'] and press(m, g, CL['B']) == WM['B'],
          'MP3: con la mano: los botones de jugar siguen igual (A, B, L = Z)')
    ingame(m, g); classic(m, ls=(1.0, 0)); kpad(m, g)
    check(hand_at(m, 0, 0), 'MP3: al acabar la sección con la mano (orden 0 activada otra vez) vuelve la mira centrada')
    ingame(m, g, hand=1); classic(m); kpad(m, g)
    check(hand_at(m, 0, 0), 'MP3: la siguiente sección con la mano empieza en el centro')
    ingame(m, g, hand=1, ball=1); classic(m, ls=(1.0, 0)); kpad(m, g)
    check(hand_at(m, 0, 0), 'MP3: en morfosfera no hay mano aunque el byte esté a 0')
    ingame(m, g, hand=1, lock=1); classic(m, ls=(1.0, 0)); kpad(m, g)
    check(hand_at(m, 0, 0), 'MP3: con blanco fijado no hay mano')
    for g in ['MP1', 'MP2']:
        m = machine(g); ingame(m, g)
        for i in range(10): classic(m, ls=(1.0, 1.0)); kpad(m, g)
        check(hand_at(m, 0, 0), f'{g}: no hay modo mano (el stick izq. no mueve la mira)')

# ---------------------------------------------------------------------------------------------------------------
# n0.6: controles de movimiento de MP3 (gancho/látigo, agitar, cerraduras/ADN, palancas)
if BS.GESTOS:
    from unicorn.ppc_const import UC_PPC_REG_MSR, UC_PPC_REG_0, UC_PPC_REG_FPR0
    def near(a, b): return abs(a - b) < 1e-5
    def run_range(m, a, b, regs=None):
        """ejecuta el código del juego (ya parcheado) de a hasta b"""
        uc = m.uc
        uc.reg_write(UC_PPC_REG_MSR, uc.reg_read(UC_PPC_REG_MSR) | 0x2000)
        for r, v in (regs or {}).items(): uc.reg_write(UC_PPC_REG_0 + r, v & 0xffffffff)
        uc.emu_start(a, b, count=1000)
    def call_fn(m, fn):
        """llama a una función del juego con bl desde un trampolín; devuelve r3"""
        T = 0x817f0000; m.w32(T, 0x48000001 | ((fn - T) & 0x03fffffc)); m.call_hook(T); return m.reg(3)
    g = 'MP3'; V = BS.VAR
    GPW, SHAKE = BS.mp3_gest()
    m = machine(g)
    check(all(m.r32(a) == v for a, v in GPW) and m.r32(BS.MP3_SHAKE[0]) >> 26 == 18,
          f'MP3: parches de gestos escritos ({len(GPW)} palabras) y el C2 de agitar instalado')
    for h in ['MP1', 'MP2', 'FE']:
        mh = machine(h); d = dolimage(h)
        bad = [hex(a) for a, v in GPW + [(BS.MP3_SHAKE[0], 0)] if d.u32(a) is not None and mh.r32(a) != d.u32(a)]
        check(not bad, f'{h}: no se aplican los parches de gestos de MP3 {bad[:4]}')
    # lanzar el látigo: L + X
    m = machine(g); ingame(m, g, orb=2)
    res = {}
    for name, b in [('L+X', CL['L'] | CL['X']), ('L', CL['L']), ('X', CL['X']), ('nada', 0), ('L+X+A', CL['L'] | CL['X'] | CL['A'])]:
        classic(m, held=b); kpad(m, g); res[name] = call_fn(m, BS.MP3_LASSO_F3)
    check(res == {'L+X': 1, 'L': 0, 'X': 0, 'nada': 0, 'L+X+A': 1}, f'MP3: látigo: se lanza con L + X mantenidos (y no con L o X solos) {res}')
    # agitar: X mantenida
    r = []
    for b in [CL['X'], 0, CL['X'] | CL['L'], CL['A']]:
        classic(m, held=b); kpad(m, g); m.call_hook(BS.MP3_SHAKE[0], regs={26: 0x1234}); r.append(m.reg(26))
    check(r == [1, 0, 1, 0], f'MP3: agitar: mientras se mantiene X (r26 = 1), si no 0 {r}')
    # tensión del látigo: stick izq. abajo
    m = machine(g); ingame(m, g, orb=2); classic(m); kpad(m, g)
    hx = []
    for i in range(30):
        classic(m, ls=(0.0, -0.8)); kpad(m, g); hx.append((round(m.rf(V + BS.V_HANDX), 4), m.r32(V + BS.V_LASSO)))
    n1 = next(i for i, (x, st) in enumerate(hx) if st == 4)
    check(near(hx[0][0], BS.LASSO_STEP) and hx[0][1] == 2 and all(st == 2 for x, st in hx[:n1]) and hx[n1][0] == 1.0
          and n1 == math.ceil(1 / BS.LASSO_STEP) - 1 and all(st == 4 and x == 1.0 for x, st in hx[n1:]),
          f'MP3: látigo: el stick izq. abajo tira (+{BS.LASSO_STEP} por frame, estado 2) y al llegar a 1 se arranca (estado 4, frame {n1 + 1})')
    check(near(m.rf(V + BS.V_HANDY), 0.25) and m.rf(KP + 0x64) == 0.0, 'MP3: látigo: brazo = tensión / 4, y mientras tiras Samus no anda hacia atrás (Nunchuk y = 0)')
    m2 = machine(g); ingame(m2, g, orb=2); classic(m2, ls=(0.5, -0.3)); kpad(m2, g)
    check(near(m2.rf(KP + 0x64), -0.3) and near(m2.rf(KP + 0x60), 0.5), 'MP3: látigo fijado sin tirar (stick a menos de la mitad): el stick sigue moviendo a Samus')
    m2 = machine(g); ingame(m2, g); classic(m2, ls=(0.0, -0.8)); kpad(m2, g)
    check(near(m2.rf(KP + 0x64), -0.8), 'MP3: sin látigo, el stick izq. abajo sigue andando hacia atrás')
    for i in range(5): classic(m, ls=(0.0, -0.4)); kpad(m, g)
    x1 = m.rf(V + BS.V_HANDX)
    for i in range(40): classic(m, ls=(0.5, 0.5)); kpad(m, g)
    check(near(x1, 1 - 5 * BS.LASSO_STEP) and m.r32(V + BS.V_LASSO) == 2 and m.rf(V + BS.V_HANDX) == 0,
          f'MP3: látigo: sin tirar (stick a menos de la mitad o hacia otro lado) la tensión baja hasta 0 {x1:.3f}')
    for i in range(3): classic(m, ls=(0.0, -1.0)); kpad(m, g)
    ingame(m, g, orb=0); classic(m, ls=(0.0, -1.0)); kpad(m, g)
    check(m.r32(V + BS.V_LASSO) == 0 and m.rf(V + BS.V_HANDX) == 0 and m.rf(V + BS.V_HANDY) == 0,
          'MP3: látigo: sin el látigo enganchado, estado 0 y tensión 0')
    # los parches del juego leen las variables
    m.w32(V + BS.V_LASSO, 4); m.wf(V + BS.V_HANDX, 0.6); m.wf(V + BS.V_HANDY, 0.15)
    f1 = BS.MP3_LASSO_F1
    run_range(m, f1, f1 + 8); run_range(m, f1 + 0xc, f1 + 0x10)
    a = m.freg(2)
    run_range(m, f1 + 0x160, f1 + 0x16c); st = m.reg(3 + 27)
    tg = [(o + (m.r32(f1 + o) & 0xfffc)) for o in (8, 0x18, 0x54)]
    check(near(a, 0.6) and st == 4 and tg == [0x160] * 3, f'MP3: ProcessGrappleLasso lee la tensión y el estado ({a:.2f}, {st}) y sus 3 saltos van al final')
    BUF = 0x81780000; m.uc.mem_write(BUF, b'\0' * 0x200)
    f2 = BS.MP3_LASSO_F2; run_range(m, f2, f2 + 0x20, {23: BUF})
    check(near(m.rf(BUF + 0x1c8), 0.15) and near(m.rf(BUF + 0x1cc), 0.6), 'MP3: animación del brazo con la tensión del látigo')
    STK = 0x81781000; OB = 0x81782000
    for j, v in enumerate([1.5, -2.5, 3.5]): m.wf(STK + 0x240 + 4 * j, v)
    sl = BS.MP3_SLIDE; run_range(m, sl, sl + 0x2c, {1: STK, 31: OB})
    check([m.rf(OB + o) for o in (0x48, 0x58, 0x68)] == [1.5, -2.5, 3.5] and m.reg(3) == OB and m.reg(4) == OB + 0x3c,
          'MP3: deslizarse por el gancho: posición directa en la matriz (parche de PrimeHack)')
    # cerraduras de combinación / escáner ADN: stick izq. a los lados
    m = machine(g); ingame(m, g); rot = []
    for lx in [0.7, -0.7, 0.3, -0.45, 1.0, 0.0]:
        classic(m, ls=(lx, 0.2)); kpad(m, g); r1 = []
        for a in BS.MP3_LOCKS:
            run_range(m, a, a + 0xc, {3: 0x81783000, 12: 0x81783000}); r1.append(round(m.freg(1), 4))
        rot.append(r1)
    R = round(BS.ROT_RATE, 4)
    check(rot == [[R, R], [-R, -R], [0, 0], [0, 0], [R, R], [0, 0]],
          f'MP3: cerradura y escáner ADN: giran ±{BS.ROT_RATE} con el stick izq. a un lado pasada la mitad, si no nada {rot}')
    # palancas / asas
    LP = 0x81784000; VT = 0x81785000; ENT = 0x81786000
    m = machine(g); ingame(m, g); m.w32(SMO + 0x1010, LP); m.w32(VT + 0xc, BS.MOTION_VF)
    ents = []   # n0.9: tipo de gesto en +0x1E4 (0 = meter/sacar, 1/2 = girar), signo en +0x1E8 ; None = puntero no válido
    def mk(i, flags=0x00100000, vt=VT, st=3, ty=0, a=1.0, b=1.0, p=0.5):
        e = ENT + 0x400 * i
        m.w32(e, vt); m.w32(e + 0x38, flags); m.w32(e + 0x14c, st); m.w32(e + 0x1e4, ty); m.w32(e + 0xd0, 2)
        m.wf(e + 0x1e8, a); m.wf(e + 0x210, b); m.wf(e + 0x154, p); return e
    E = [mk(0, ty=0, a=1.0, b=-1.0), mk(1, ty=2, a=1.0, b=-1.0), mk(2, ty=0, a=-1.0), mk(3, ty=1, a=-1.0, b=1.0), mk(4, st=2),
         mk(5, vt=VT + 0x100), mk(6, flags=0), mk(7, flags=0x20000000), mk(8, flags=0x20200000), 0, mk(10, vt=0x12345678),
         mk(11, p=0.98), mk(12, a=-1.0, p=0.02)]
    order = list(range(len(E)))
    for k, i in enumerate(order):
        m.w32(LP + 4 + 8 * i, E[i]); m.uc.mem_write(LP + 4 + 8 * i + 6, struct.pack('>H', order[k + 1] if k + 1 < len(order) else 0xffff))
    def prog(): return [round(m.rf(e + 0x154), 4) if e else None for e in E]
    p0 = prog(); S = BS.LEVER_STEP
    classic(m, ls=(0.0, -1.0)); kpad(m, g); p1 = prog()
    classic(m, ls=(-0.8, 0.0)); kpad(m, g); p2 = prog()
    classic(m, ls=(0.3, 0.15)); kpad(m, g); p3 = prog()
    exp1 = [0.55, 0.5, 0.45, 0.5, 0.5, 0.5, 0.5, 0.55, 0.5, None, 0.5, 1.0, 0.0]
    exp2 = [0.55, 0.45, 0.45, 0.55, 0.5, 0.5, 0.5, 0.55, 0.5, None, 0.5, 1.0, 0.0]
    check(p1 == exp1, f'MP3: palanca/célula de meter y sacar (tipo 0): el stick izq. abajo/arriba la mueve ±{S} según el sentido de su paso, con tope 0..1 {p1}')
    check(p2 == exp2, f'MP3: girar (tipos 1 y 2, p. ej. la célula): stick izq. a los lados según el signo de +0x1E8, al revés que meter/sacar (n0.10, probado por Adrián) {p2}')
    check(p3 == p2, 'MP3: palancas: con el stick a menos de la mitad no se mueven')
    check(p1[4:7] == [0.5] * 3 and p1[8] == 0.5 and p1[10] == 0.5,
          'MP3: palancas: solo las agarradas (estado 3), de la clase de PrimeHack y activas; punteros malos se saltan')
    ingame(m, g, menu=1); classic(m, ls=(0.0, -1.0)); kpad(m, g)
    check(prog() == p2, 'MP3: palancas: en la pausa no se mueven')
    m.uc.mem_write(LP + 4 + 6, struct.pack('>H', 0)); ingame(m, g); classic(m, ls=(0.0, -1.0)); kpad(m, g)
    check(prog()[0] == 1.0, 'MP3: palancas: una lista en bucle no cuelga (tope de 2048 objetos)')
    for h in ['MP1', 'MP2']:
        mh = machine(h); ingame(mh, h, orb=G[h]['f']['orbv'])
        for i in range(5): classic(mh, ls=(0.9, -1.0)); kpad(mh, h)
        check(all(mh.r32(V + o) == 0 for o in (BS.V_LASSO, BS.V_HANDX, BS.V_HANDY, BS.V_ROT)),
              f'{h}: los gestos de MP3 no corren (variables a 0)')

# ---------------------------------------------------------------------------------------------------------------
# n0.10: MP1/MP2, cruceta izq./der. jugando = rayo anterior / siguiente, saltando los que no tienes
INV = 0x81790000
for g in ['MP1', 'MP2']:
    Bm = G[g]['beam']; order = [(Bm['order'] >> (24 - 8 * k)) & 0xff for k in range(4)]
    def setup(m, have):
        if g == 'MP1': m.w32(0x804c3c14, INV); m.w32(INV, INV + 0x100)
        else: m.w32(0x804f0000 - 0x3d4, INV); m.w32(INV + 0x12ec, INV + 0x100)
        for b in range(4): m.w32(INV + 0x100 + Bm['off'] + Bm['size'] * b, 1 if b in have else 0)
    def beamhook(m, cur):
        gun = 0x81791000; m.w32(gun + Bm['cur'], cur)
        m.call_hook(Bm['at'], regs={Bm['gun']: gun, Bm['beamreg']: 0xffffffff, Bm['pidreg']: 0xffffffff})
        return m.reg(Bm['beamreg']) if m.reg(Bm['beamreg']) != 0xffffffff else -1
    res = []
    for have, cur, btn in [((0, 1, 2, 3), order[0], 'RIGHT'), ((0, 1, 2, 3), order[0], 'LEFT'), ((0, order[3]), order[0], 'RIGHT'),
                           ((0,), 0, 'RIGHT'), ((0, 1, 2, 3), order[1], 'RIGHT')]:
        m = machine(g); ingame(m, g); setup(m, have)
        classic(m, held=CL[btn], trig=CL[btn]); kpad(m, g); r1 = beamhook(m, cur); r2 = beamhook(m, cur)
        res.append((r1, r2))
    exp = [(order[1], -1), (order[3], -1), (order[3], -1), (-1, -1), (order[2], -1)]
    check(res == exp, f'{g}: cruceta der./izq. jugando = rayo siguiente / anterior (orden {order}), saltando los que no tienes; una vez por pulsación {res}')
    m = machine(g); ingame(m, g); setup(m, (0, 1, 2, 3))
    classic(m, held=CL['RIGHT'], trig=0); kpad(m, g); r = beamhook(m, order[0])
    ingame(m, g, menu=4); classic(m, held=CL['RIGHT'], trig=CL['RIGHT']); kpad(m, g); ingame(m, g); classic(m); kpad(m, g)
    r3 = beamhook(m, order[0])
    check(r == -1 and r3 == -1, f'{g}: el rayo solo cambia al pulsar (no manteniendo) y no desde los menús')
    m = machine(g); ingame(m, g); m.w32(0x804c3c14 if g == 'MP1' else 0x804f0000 - 0x3d4, 0)
    classic(m, held=CL['RIGHT'], trig=CL['RIGHT']); kpad(m, g)
    check(beamhook(m, order[0]) == -1, f'{g}: cambio de rayo sin inventario (puntero nulo): no hace nada')
for h in ['MP3', 'FE']:
    mh = machine(h); d = dolimage(h)
    check(all(d.u32(G[x]['beam']['at']) is None or mh.r32(G[x]['beam']['at']) == d.u32(G[x]['beam']['at']) for x in ['MP1', 'MP2']),
          f'{h}: no se aplican los ganchos del cambio de rayo')

# ---------------------------------------------------------------------------------------------------------------
# n0.8: MP1, aviso de salir de la partida (dentro de la pausa): la cruceta izq./der. es la del Wiimote
m = machine('MP1'); ingame(m, 'MP1', menu=2)
p0 = (press(m, 'MP1', CL['LEFT']), press(m, 'MP1', CL['RIGHT']))
qa, qorig = G['MP1']['quit']
def qpress(c): m.call_hook(qa, regs={1: 0x80f00000}); return press(m, 'MP1', CL[c])
q = [qpress(c) for c in ['LEFT', 'RIGHT', 'A', 'B', 'UP']]
for i in range(BS.CNT + 1): classic(m); kpad(m, 'MP1')
p1 = (press(m, 'MP1', CL['LEFT']), press(m, 'MP1', CL['RIGHT']))
check(p0 == (WM['MINUS'], WM['PLUS']) and q == [WM['LEFT'], WM['RIGHT'], WM['A'], WM['B'], WM['UP']] and p1 == p0,
      f'MP1: aviso de salir: cruceta izq./der. = izq./der. del Wiimote (en la pausa sin aviso, − / +); al cerrarlo vuelve {p0} {q} {p1}')
for h in ['MP2', 'MP3', 'FE']:
    mh = machine(h); d = dolimage(h)
    check(d.u32(qa) is None or mh.r32(qa) == d.u32(qa), f'{h}: no se aplica el gancho del aviso de salir de MP1')

# ---------------------------------------------------------------------------------------------------------------
# MP3: estado de control (PrimeHack): no se escribe en el jugador, sí en los demás objetos
m = machine('MP3'); ingame(m, 'MP3')
OBJ = 0x81740000
m.w32(0x805ca0c0 + 0x2c, 0x81720000); m.w32(0x81720004, SMO)   # *(*(0x805CA0EC)+4)+0x2184 = jugador
m.w32(PL + 0x78, 0); m.call_hook(0x8000ab58, regs={31: PL, 3: PL, 6: 0x1234})
a = m.r32(PL + 0x78)
m.w32(OBJ + 0x78, 0); m.call_hook(0x8000ab58, regs={31: OBJ, 3: OBJ, 6: 0x1234})
check(a == 0 and m.r32(OBJ + 0x78) == 0x1234, 'MP3: estado de control: el jugador no lo recibe, otros objetos sí')

# ---------------------------------------------------------------------------------------------------------------
# el código funciona igual aunque haya otros códigos delante en la lista
prefix = bytes.fromhex('04001000 12345678'.replace(' ', '')) * 3
m = machine('MP1', prefix); ingame(m, 'MP1')
ok = m.r32(0x80001000) == 0x12345678 and press(m, 'MP1', CL['ZR']) == WM['DOWN']
classic(m, rs=(1.0, 0)); xf0 = m.rd(PL + 0x2c, 48); kpad(m, 'MP1')
check(ok and m.rd(PL + 0x2c, 48) != xf0, 'con otros códigos delante en la lista todo sigue funcionando')

# ---------------------------------------------------------------------------------------------------------------
# n0.6: con la lista comprimida, jugar no cambia su suma de control (si cambiara, se descomprimiría en cada frame) y
# el descompresor no vuelve a correr; si se pisa la lista (carga de otro .dol), se descomprime otra vez
if INFO:
    import unpack_asm as UA, build_gct as BG
    NL = INFO['lista']; PAY = UNC + b''.join(bytes.fromhex(l.replace(' ', '')) for l in UA.ret_c0_lines(BG.RET))
    for g in ALL + ['FE']:
        m = machine(g)
        if g != 'FE': ingame(m, g)
        for c in ['A', 'PLUS', 'DOWN', 'UP', 'X']: press(m, g, CL[c]); classic(m); kpad(m, g)
        if g != 'FE':
            ingame(m, g, ball=1); press(m, g, CL['X']); ingame(m, g, menu=1); press(m, g, CL['A'])
        same = UA.list_sum(m.rd(LIST, NL)) == UA.list_sum(PAY)
        runs = []
        hk = m.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: runs.append(a), begin=0x80002340, end=0x80003000)
        m.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: runs.append(-1), begin=LIST + 8, end=LIST + 12)
        m.run_codehandler(50_000_000)
        n1 = len(runs); runs.clear()
        m.w32(LIST + 0x100, 0); m.run_codehandler(50_000_000); n2 = len(runs)
        check(same and n1 < 20000 and n2 > 100000 and UA.list_sum(m.rd(LIST, NL)) == UA.list_sum(PAY),
              f'{g}: lista comprimida: jugando no cambia (el descompresor no corre: {n1} instr. en el C0) y si se pisa se vuelve a descomprimir ({n2})')

# ---------------------------------------------------------------------------------------------------------------
# cobertura del código común
body_lo = LIST + 8; body_hi = body_lo + 8 * int(L[0].split()[1], 16)
import capstone
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN); md.skipdata = True
blob = UNC[8:8 + (body_hi - body_lo)]
data_lo = 0x80002340 + AT['core'] + 4 * (core_isclassic := 0)   # (las constantes no son instrucciones)
unc = [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in md.disasm(blob, body_lo)
       if i.address not in covered and i.address != body_lo]
consts = len(BS.K) + len(BS.table()[0])
print(f'código común: {len(unc)} palabras sin ejecutar (de ellas {consts} son constantes y tabla, más el relleno final)')
for u in unc[:80]: print('   ', u)
print('FALLOS:', len(fails))
