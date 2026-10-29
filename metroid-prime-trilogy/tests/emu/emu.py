"""Banco de pruebas: emula el codehandler Gecko de Dolphin y los ganchos del mod con Unicorn (PPC 750)."""
import struct, os
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_PPC32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UcError
from unicorn.ppc_const import *
from dolr import Dol
HERE = os.path.dirname(os.path.abspath(__file__))
# .dol de Trilogy: por defecto ..\\..\\data\\files (la extracción del disco junto a la rama); se puede cambiar con DOLS
DOLS = os.environ.get('DOLS', os.path.join(HERE, '..', '..', 'data', 'files')) + os.sep
GAMEDOL = {'MP1': 'rs5mp1_p.dol', 'MP2': 'rs5mp2_p.dol', 'MP3': 'rs5mp3_p.dol', 'FE': 'rs5fe_p.dol'}
CH = open(os.path.join(HERE, 'codehandler.bin'), 'rb').read()   # gestor de códigos de Dolphin
STOP = 0x81700000
_dolcache = {}
def dolimage(g):
    if g not in _dolcache:
        d = Dol(DOLS + GAMEDOL[g]); _dolcache[g] = d
    return _dolcache[g]

class Machine:
    def __init__(s, game):
        s.game = game
        s.uc = uc = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        try: uc.ctl_set_cpu_model(UC_CPU_PPC32_750_V3_1)
        except Exception: pass
        uc.mem_map(0x80000000, 0x01800000)
        uc.mem_map(0x90000000, 0x01000000)
        uc.mem_map(0xCC000000, 0x00010000)
        uc.mem_map(0xCD000000, 0x00010000)
        d = dolimage(game)
        for va, o, z, i in d.segs:
            uc.mem_write(va, d.d[o:o+z])
        uc.mem_write(0x80001800, CH)
        s.writes = []
    # memory helpers
    def r32(s, a): return struct.unpack('>I', s.uc.mem_read(a, 4))[0]
    def w32(s, a, v): s.uc.mem_write(a, struct.pack('>I', v & 0xffffffff))
    def r8(s, a): return s.uc.mem_read(a, 1)[0]
    def w8(s, a, v): s.uc.mem_write(a, bytes([v & 0xff]))
    def rf(s, a): return struct.unpack('>f', s.uc.mem_read(a, 4))[0]
    def wf(s, a, v): s.uc.mem_write(a, struct.pack('>f', v))
    def rd(s, a, n): return bytes(s.uc.mem_read(a, n))
    def install(s, gct_codes: bytes, limit=0x80003000):
        """gct_codes: bytes of the code list WITHOUT header/footer."""
        base = 0x80001800 + len(CH) - 8
        assert base == 0x80002338
        blob = bytes.fromhex('00D0C0DE00D0C0DE') + gct_codes + bytes.fromhex('F000000000000000')
        assert base + len(blob) <= limit, len(blob)
        s.uc.mem_write(base, blob)
        s.w32(0x80001800, 0xD01F1BAD)
        s.w8(0x80001807, 1)
        s.w32(STOP, 0)
    def run_codehandler(s, max_ins=2_000_000):
        uc = s.uc
        uc.reg_write(UC_PPC_REG_1, 0x80F00000)
        uc.reg_write(UC_PPC_REG_LR, STOP)
        msr = uc.reg_read(UC_PPC_REG_MSR) if hasattr(__import__('unicorn').ppc_const, 'UC_PPC_REG_MSR') else None
        uc.emu_start(0x800018A8, STOP, count=max_ins)
        assert uc.reg_read(UC_PPC_REG_PC) == STOP, hex(uc.reg_read(UC_PPC_REG_PC))
    def call_hook(s, addr, regs=None, fregs=None, max_ins=500_000, track=False):
        """Run game code from `addr` (where the codehandler wrote the branch) until it returns to addr+4."""
        uc = s.uc
        uc.reg_write(UC_PPC_REG_MSR, uc.reg_read(UC_PPC_REG_MSR) | 0x2000)   # FP disponible (como en el juego)
        for r, v in (regs or {}).items(): uc.reg_write(UC_PPC_REG_0 + r, v & 0xffffffff)
        for r, v in (fregs or {}).items(): uc.reg_write(UC_PPC_REG_FPR0 + r, struct.unpack('>Q', struct.pack('>d', v))[0])
        uc.reg_write(UC_PPC_REG_1, uc.reg_read(UC_PPC_REG_1) if regs and 1 in regs else 0x80F00000)
        s.writes = []
        h = None
        if track:
            def hw(uc_, access, a, size, val, ud): s.writes.append((a, size, val))
            h = uc.hook_add(UC_HOOK_MEM_WRITE, hw)
        try:
            uc.emu_start(addr, addr + 4, count=max_ins)
        finally:
            if h is not None: uc.hook_del(h)
        pc = uc.reg_read(UC_PPC_REG_PC)
        assert pc == addr + 4, f'hook did not return: pc={pc:08x}'
    def freg(s, r):
        return struct.unpack('>d', struct.pack('>Q', s.uc.reg_read(UC_PPC_REG_FPR0 + r)))[0]
    def reg(s, r): return s.uc.reg_read(UC_PPC_REG_0 + r)

def gct_from_lines(lines):
    return b''.join(bytes.fromhex(l.replace(' ', '')) for l in lines)

# ---- deterministic time base for mftb ----
def install_timebase(m, ranges):
    m.tb = 0x10000000
    m._mftb_rd = None
    def hk(uc, addr, size, ud):
        if m._mftb_rd is not None:
            uc.reg_write(UC_PPC_REG_0 + m._mftb_rd, m.tb & 0xffffffff); m._mftb_rd = None
        w = struct.unpack('>I', uc.mem_read(addr, 4))[0]
        if (w & 0xFC1FFFFF) == 0x7C0C42E6: m._mftb_rd = (w >> 21) & 31
    for lo, hi in ranges: m.uc.hook_add(UC_HOOK_CODE, hk, begin=lo, end=hi)
