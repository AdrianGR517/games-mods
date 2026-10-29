"""Simula que el menú carga el .dol de un juego a trozos mientras el gestor de códigos sigue corriendo (rama nueva)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'src'))
# emulador (emu.py, codehandler.bin) de la rama unificada; con EMU se puede indicar otra carpeta
sys.path.insert(0, os.environ.get('EMU', os.path.join(HERE, 'emu')))
import base as BS
from emu import Machine, dolimage
L, CODES, AT, SIZES, INFO = BS.final()   # n0.6: comprimido
def trial(src, dst, chunk, order):
    m = Machine(src); m.install(CODES)
    for _ in range(2): m.run_codehandler(50_000_000)
    d = dolimage(dst)
    segs = d.segs if order == 'dol' else list(reversed(d.segs))
    runs = 0
    for va, o, z, i in segs:
        ks = range(0, z, chunk)
        for k in (ks if order != 'rev' else reversed(ks)):
            m.uc.mem_write(va + k, d.d[o + k:o + min(k + chunk, z)]); runs += 1
            try: m.run_codehandler(50_000_000)
            except Exception as e: return runs, f'CUELGUE ({e})'
    for _ in range(2): m.run_codehandler(50_000_000)
    ref = Machine(dst); ref.install(CODES)
    for _ in range(2): ref.run_codehandler(50_000_000)
    bad = []
    for va, o, z, i in d.segs:
        a = m.rd(va, z); b = ref.rd(va, z)
        bad += [va + j for j in range(0, z, 4) if a[j:j+4] != b[j:j+4] and not (0x80004134 <= va + j < 0x80006068)]
    return runs, 'igual que una carga limpia' if not bad else 'DISTINTA ' + ' '.join(hex(x) for x in bad[:6])
for src, dst in [('FE','MP1'), ('FE','MP2'), ('FE','MP3'), ('MP1','FE'), ('MP2','FE'), ('MP3','FE')]:
    for chunk in [0x8000, 0x800, 0x100, 0x20]:
        for order in ['dol', 'rev']:
            r, res = trial(src, dst, chunk, order)
            print(src, '->', dst, hex(chunk), order, 'pasadas', r, ':', res, flush=True)
