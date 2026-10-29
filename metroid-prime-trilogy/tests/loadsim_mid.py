"""n0.9: el menú carga el .dol encima de la zona TRK MIENTRAS el descompresor está a medias (en Dolphin la carga
puede caer entre dos bloques del gestor de códigos). Comprueba que nada escribe fuera de la lista, las variables,
la pila y el gestor, y que después todo queda como en una carga limpia. Con GCT=ruta se prueba otro .gct.
STRICT=0: no falla por escribir fuera (con el gestor de USB Loader GX el emulador sí ve los parches del juego
de origen, que siguen en memoria; lo que cuenta es que al final quede como una carga limpia)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src'))
sys.path.insert(0, os.environ.get('EMU', os.path.join(HERE, 'emu')))
import base as BS
from emu import Machine, dolimage, STOP
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.ppc_const import UC_PPC_REG_PC, UC_PPC_REG_1, UC_PPC_REG_LR
if os.environ.get('GCT'): CODES = open(os.environ['GCT'], 'rb').read()[8:-8]
else: CODES = BS.final()[1]
OK = [(0x80001800, 0x80003000), (0x80004134, 0x80006068), (0x80E00000, 0x80F00010), (0xCC000000, 0xCD000000)]
def trial(src, dst, k):
    m = Machine(src); m.install(CODES)
    for _ in range(2): m.run_codehandler(50_000_000)
    d = dolimage(dst); uc = m.uc
    seg = [(va, o, z) for va, o, z, i in d.segs if va <= 0x80004180 < va + z][0]
    va, o, z = seg
    lo, hi = 0x80004134, min(va + z, 0x80006068)
    uc.mem_write(0x80004180, bytes(0x40))       # primer trozo: rompe la suma -> descomprime
    bad = []
    h = uc.hook_add(UC_HOOK_MEM_WRITE, lambda u, a_, addr, sz, v, ud: bad.append(addr) if not any(a <= addr < b for a, b in OK) else None)
    uc.reg_write(UC_PPC_REG_1, 0x80F00000); uc.reg_write(UC_PPC_REG_LR, STOP)
    try:
        uc.emu_start(0x800018A8, STOP, count=k)
        pc = uc.reg_read(UC_PPC_REG_PC)
        if pc != STOP:
            uc.mem_write(lo, d.d[o + lo - va:o + hi - va])       # el resto de la zona, de golpe, a mitad
            uc.emu_start(pc, STOP, count=50_000_000)
    except Exception as e: return f'CUELGUE ({e}, escrituras fuera: {[hex(x) for x in bad[:3]]})'
    uc.hook_del(h)
    if bad and os.environ.get("STRICT","1")=="1": return "ESCRIBE FUERA " + " ".join(hex(x) for x in bad[:4])
    if bad: print("   (escrituras fuera:", " ".join(hex(x) for x in sorted(set(bad))[:6]), ")")
    for va2, o2, z2, i in d.segs: m.uc.mem_write(va2, d.d[o2:o2 + z2])
    for _ in range(3): m.run_codehandler(50_000_000)
    ref = Machine(dst); ref.install(CODES)
    for _ in range(3): ref.run_codehandler(50_000_000)
    diff = [x for va2, o2, z2, i in d.segs for x in range(va2, va2 + z2, 4) if m.rd(x, 4) != ref.rd(x, 4) and not (0x80004134 <= x < 0x80006068)]
    return 'bien' if not diff else 'DISTINTA ' + ' '.join(hex(x) for x in diff[:4])
fails = 0
for src, dst in [('MP2', 'FE'), ('FE', 'MP3'), ('MP1', 'FE'), ('FE', 'MP1'), ('MP3', 'FE'), ('FE', 'MP2')]:
    res = {}
    for k in [2000, 60000, 250000, 600000]:
        r = trial(src, dst, k); res.setdefault(r, []).append(k)
        if r != 'bien': fails += 1
    print(f'{src}->{dst}:', '; '.join(f'{r} (k={ks})' for r, ks in res.items()))
print('FALLOS:', fails)
