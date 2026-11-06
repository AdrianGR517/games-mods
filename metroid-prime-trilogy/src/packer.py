"""Compresor LZ + codificador aritmético binario adaptativo (estilo LZMA) para el código Gecko.
El descompresor en PowerPC (unpack_asm.py) sigue exactamente el mismo modelo que decode() de aquí.

Modelo (pensado para que el descompresor sea lo más corto posible):
- Probabilidades de 12 bits, empiezan en 2048, adaptación >>4. Rango de 32 bits; se normaliza una sola vez por bit
  (si el rango baja de 2^24 se mete un byte). El codificador comprueba que la ida y vuelta sale bien.
- El primer byte es siempre un literal y no lleva bit de tipo.
- Antes de cada símbolo: bit de tipo (0 literal, 1 copia), contexto 48 + 4*prev_copia + ((pos-1)&3).
- Literal: 8 bits MSB primero con árbol. Nibble alto: contexto ((pos-1)&3)*16 + nodo (nodo 1..15);
  nibble bajo: contexto 48 + nodo (nodo 16..255).
- Copia: bit "repetir desplazamiento" (contexto 56 + 4*prev_copia). Si no repite: número n = ((off-1)>>2)+1
  (gamma de Elias: unario en OFF+i, bits en OFF-k) y luego los 2 bits bajos de off-1 (contextos 57 y 58).
  Después la longitud L>=2 con el mismo tipo de número en LEN.
"""
import math, collections

class Cfg:
    PB = 12            # bits de probabilidad
    SH = 4             # velocidad de adaptación
    MAXLEN = 255
    WINDOW = 1 << 13
    NUB = 16           # máximo de bits de un número
    NORM_ONCE = True   # normalizar como mucho un byte por bit
    LOWTREE = False    # bits bajos del desplazamiento: árbol (True) o independientes (False)
    REPM = True        # el bit de repetir se codifica también después de una copia
    RANGE0 = 0x80000000  # rango inicial

def layout(cfg):
    # 0..63: nibble alto de los literales (4 posiciones x 16), 64..303: nibble bajo (48 + nodo 16..255)
    o = {'KIND': 304, 'REP': 312, 'LOW': 313}
    base = 317
    o['OFF'] = base + cfg.NUB - 1       # bits en OFF-(NUB-1)..OFF-1, unario en OFF..OFF+NUB-1
    o['LEN'] = o['OFF'] + cfg.NUB + cfg.NUB - 1
    o['N'] = o['LEN'] + cfg.NUB
    return o

def kind_ctx(o, prevm, pos): return o['KIND'] + 4*prevm + ((pos - 1) & 3)
def rep_ctx(o, prevm): return o['REP'] + 4*prevm
def lit_ctx(o, pos, node):
    if node < 16: return ((pos - 1) & 3)*16 + node
    return 48 + node
def low_ctxs(cfg, o, h):
    if cfg.LOWTREE: return o['LOW'], o['LOW'] + 1 + h
    return o['LOW'], o['LOW'] + 1

# ---------------- codificador de rango ----------------
class Enc:
    def __init__(s, cfg):
        s.cfg = cfg; s.low = 0; s.range = cfg.RANGE0; s.cache = 0; s.csize = 1; s.out = bytearray()
    def shift_low(s):
        if s.low < 0xFF000000 or s.low >= (1 << 32):
            carry = s.low >> 32
            tmp = s.cache
            while True:
                s.out.append((tmp + carry) & 0xFF)
                tmp = 0xFF
                s.csize -= 1
                if s.csize == 0: break
            s.cache = (s.low >> 24) & 0xFF
        s.csize += 1
        s.low = (s.low << 8) & 0xFFFFFFFF
    def bit(s, probs, i, b):
        cfg = s.cfg; p = probs[i]
        bound = (s.range >> cfg.PB) * p
        assert 0 < bound < s.range
        if b == 0:
            s.range = bound; probs[i] = p + (((1 << cfg.PB) - p) >> cfg.SH)
        else:
            s.low += bound; s.range -= bound; probs[i] = p - (p >> cfg.SH)
        if cfg.NORM_ONCE:
            if s.range < (1 << 24): s.range = (s.range << 8) & 0xFFFFFFFF; s.shift_low()
        else:
            while s.range < (1 << 24): s.range = (s.range << 8) & 0xFFFFFFFF; s.shift_low()
    def finish(s):
        for _ in range(5): s.shift_low()
        assert s.out[0] == 0
        return bytes(s.out[1:])

class Dec:
    """Igual que el PowerPC: code/range de 32 bits, lee bytes de data (0 si se acaba)."""
    def __init__(s, cfg, data):
        s.cfg = cfg; s.d = data; s.i = 4; s.range = cfg.RANGE0
        s.code = int.from_bytes(data[0:4], 'big'); s.maxread = 4
    def bit(s, probs, i):
        cfg = s.cfg; p = probs[i]
        bound = ((s.range >> cfg.PB) * p) & 0xFFFFFFFF
        if s.code >= bound:      # subfc: CA = code >= bound
            s.code -= bound; s.range = (s.range - bound) & 0xFFFFFFFF; probs[i] = p - (p >> cfg.SH); b = 1
        else:
            s.range = bound; probs[i] = p + (((1 << cfg.PB) - p) >> cfg.SH); b = 0
        n = 1 if cfg.NORM_ONCE else 4
        for _ in range(n):
            if s.range & 0xFF000000: break
            s.range = (s.range << 8) & 0xFFFFFFFF
            s.code = ((s.code << 8) | (s.d[s.i] if s.i < len(s.d) else 0)) & 0xFFFFFFFF; s.i += 1
            s.maxread = max(s.maxread, s.i)
        return b

# ---------------- números (gamma de Elias con contextos) ----------------
def num_bits(base, n, cfg):
    """lista de (contexto, bit) para el número n>=1"""
    assert 1 <= n < (1 << (cfg.NUB - 1))
    nb = n.bit_length() - 1; L = []
    for i in range(nb): L.append((base + i, 1))
    L.append((base + nb, 0))
    for i in range(nb - 1, -1, -1): L.append((base - (i + 1), (n >> i) & 1))
    return L
def dec_number(dd, probs, base, cfg):
    k = 0
    while dd.bit(probs, base + k): k += 1
    n = 1
    while k: n = 2*n + dd.bit(probs, base - k); k -= 1
    return n

# ---------------- secuencia de bits de una tokenización (la usan codificador y estadísticas) ----------------
def symbols(data, toks, cfg):
    """genera (tipo, contexto, bit) en el orden exacto en que el descompresor los lee"""
    o = layout(cfg); pos = 0; prevm = 0; rep = None
    for t in toks:
        if t[0] == 'L':
            if pos > 0: yield ('kind', kind_ctx(o, prevm, pos), 0)
            node = 1; b = data[pos]
            for k in range(7, -1, -1):
                bit = (b >> k) & 1; yield ('lit', lit_ctx(o, pos, node), bit); node = node*2 + bit
            pos += 1; prevm = 0
        else:
            _, L, off = t
            assert pos > 0
            yield ('kind', kind_ctx(o, prevm, pos), 1)
            isrep = 1 if off == rep else 0
            if prevm and not cfg.REPM: isrep = 0
            else: yield ('rep', rep_ctx(o, prevm), isrep)
            if not isrep:
                n = ((off - 1) >> 2) + 1
                for c, b in num_bits(o['OFF'], n, cfg): yield ('off', c, b)
                lb = (off - 1) & 3; c1, c0 = low_ctxs(cfg, o, lb >> 1)
                yield ('low', c1, lb >> 1); yield ('low', c0, lb & 1)
                rep = off
            for c, b in num_bits(o['LEN'], L, cfg): yield ('len', c, b)
            pos += L; prevm = 1
    assert pos == len(data)

def encode(data, toks, cfg):
    o = layout(cfg); probs = [1 << (cfg.PB - 1)] * o['N']; e = Enc(cfg)
    for _, c, b in symbols(data, toks, cfg):
        assert 0 <= c < o['N']
        e.bit(probs, c, b)
    return e.finish()

def decode(blob, n, cfg, info=None):
    o = layout(cfg); probs = [1 << (cfg.PB - 1)] * o['N']
    dd = Dec(cfg, blob); out = bytearray(); prevm = 0; rep = None
    first = True
    while len(out) < n:
        pos = len(out)
        if first or dd.bit(probs, kind_ctx(o, prevm, pos)) == 0:
            first = False
            node = 1
            for _ in range(8): node = node*2 + dd.bit(probs, lit_ctx(o, pos, node))
            out.append(node & 0xFF); prevm = 0
        else:
            if (prevm and not cfg.REPM) or not dd.bit(probs, rep_ctx(o, prevm)):
                nn = dec_number(dd, probs, o['OFF'], cfg)
                c1, _ = low_ctxs(cfg, o, 0)
                h = dd.bit(probs, c1); _, c0 = low_ctxs(cfg, o, h); l = dd.bit(probs, c0)
                rep = 4*nn + 2*h + l - 3
            L = dec_number(dd, probs, o['LEN'], cfg)
            for _ in range(L): out.append(out[-rep])
            prevm = 1
    if info is not None: info['maxread'] = dd.maxread; info['len'] = len(out)
    return bytes(out[:n])

# ---------------- tokenización (programación dinámica con costes estimados) ----------------
def matches_at(data, i, cfg):
    n = len(data); best = {}
    lo = max(0, i - cfg.WINDOW)
    for j in range(i - 1, lo - 1, -1):
        if data[j] != data[i]: continue
        k = 0
        while i + k < n and data[j + k] == data[i + k] and k < cfg.MAXLEN: k += 1
        if k >= 2:
            off = i - j
            for L in range(2, k + 1):
                if L not in best or off < best[L]: best[L] = off
    return best

class CostModel:
    def __init__(s, st=None): s.st = st
    def lit(s, b, pos): return 8.5 if s.st is None else s.st['lit'][pos & 3].get(b, 11.0)
    def kind(s, prevm, k): return 1.0 if s.st is None else s.st['kind'][prevm][k]
    def rep(s, prevm, b): return 1.0 if s.st is None else s.st['rep'][prevm][b]
    def num(s, which, n):
        nb = n.bit_length() - 1
        if s.st is None: return (2*nb + 1) * 0.9
        return s.st[which].get(nb, 2*nb + 1)
    def low(s, lb): return 2.0 if s.st is None else s.st['low'][lb]

def parse_dp(data, cfg, cm, mcache):
    n = len(data); INF = float('inf')
    cost = [INF] * (n + 1); back = [None] * (n + 1); repat = [None] * (n + 1); pm = [0] * (n + 1)
    cost[0] = 0.0
    for i in range(n):
        if cost[i] == INF: continue
        c0 = cost[i]; prevm = pm[i]; rep = repat[i]
        c = c0 + (cm.kind(prevm, 0) if i else 0) + cm.lit(data[i], i)
        if c < cost[i + 1]: cost[i + 1] = c; back[i + 1] = ('L', i); repat[i + 1] = rep; pm[i + 1] = 0
        if i == 0: continue
        if rep is not None and i - rep >= 0 and (cfg.REPM or not prevm):
            k = 0
            while i + k < n and data[i - rep + k] == data[i + k] and k < cfg.MAXLEN: k += 1
            for L in range(2, k + 1):
                c = c0 + cm.kind(prevm, 1) + cm.rep(prevm, 1) + cm.num('len', L)
                if c < cost[i + L]: cost[i + L] = c; back[i + L] = ('M', i, L, rep); repat[i + L] = rep; pm[i + L] = 1
        for L, off in mcache[i].items():
            if off == rep and (cfg.REPM or not prevm): continue
            c = (c0 + cm.kind(prevm, 1) + (cm.rep(prevm, 0) if (cfg.REPM or not prevm) else 0) + cm.num('off', ((off - 1) >> 2) + 1)
                 + cm.low((off - 1) & 3) + cm.num('len', L))
            if c < cost[i + L]: cost[i + L] = c; back[i + L] = ('M', i, L, off); repat[i + L] = off; pm[i + L] = 1
    toks = []; i = n
    while i > 0:
        b = back[i]
        if b[0] == 'L': toks.append(('L',)); i = b[1]
        else: toks.append(('M', b[2], b[3])); i = b[1]
    toks.reverse()
    return toks

def stats_from(data, toks, cfg):
    """costes adaptativos medidos de una tokenización -> modelo de costes estático para la siguiente pasada"""
    o = layout(cfg); probs = [1 << (cfg.PB - 1)] * o['N']
    def cost_bit(i, b):
        p = probs[i] / (1 << cfg.PB); q = p if b == 0 else 1 - p
        if b == 0: probs[i] += ((1 << cfg.PB) - probs[i]) >> cfg.SH
        else: probs[i] -= probs[i] >> cfg.SH
        return -math.log2(max(q, 1e-6))
    # agrupa los bits por símbolo recorriendo los tokens en paralelo con symbols()
    st = {'lit': [collections.defaultdict(list) for _ in range(4)], 'kind': [[[], []], [[], []]],
          'rep': [[[], []], [[], []]], 'off': collections.defaultdict(list), 'len': collections.defaultdict(list),
          'low': collections.defaultdict(list)}
    gen = symbols(data, toks, cfg); pos = 0; prevm = 0; rep = None; total = 0.0
    def take(k):
        nonlocal total
        c = 0.0
        for _ in range(k):
            _, ctx, b = next(gen); c += cost_bit(ctx, b)
        total += c; return c
    for t in toks:
        if t[0] == 'L':
            if pos: st['kind'][prevm][0].append(take(1))
            st['lit'][pos & 3][data[pos]].append(take(8)); pos += 1; prevm = 0
        else:
            _, L, off = t
            st['kind'][prevm][1].append(take(1))
            isrep = 1 if off == rep else 0
            if prevm and not cfg.REPM: isrep = 0
            else: st['rep'][prevm][isrep].append(take(1))
            if not isrep:
                n = ((off - 1) >> 2) + 1; nb = n.bit_length() - 1
                st['off'][nb].append(take(2*nb + 1)); st['low'][(off - 1) & 3].append(take(2)); rep = off
            nb = L.bit_length() - 1; st['len'][nb].append(take(2*nb + 1))
            pos += L; prevm = 1
    avg = lambda l, d: (sum(l) / len(l)) if l else d
    S = {'lit': [{b: avg(v, 11) for b, v in st['lit'][p].items()} for p in range(4)],
         'kind': [[avg(st['kind'][pm][k], 1.5) for k in (0, 1)] for pm in (0, 1)],
         'rep': [[avg(st['rep'][pm][k], 2) for k in (0, 1)] for pm in (0, 1)],
         'off': {k: avg(v, 2*k + 1) for k, v in st['off'].items()},
         'len': {k: avg(v, 2*k + 1) for k, v in st['len'].items()},
         'low': {k: avg(st['low'][k], 2.0) for k in range(4)}}
    return S, total / 8

def compress(data, cfg=None, iters=5, verbose=False):
    cfg = cfg or Cfg()
    mcache = [matches_at(data, i, cfg) for i in range(len(data))]
    cm = CostModel(); best = None
    for it in range(iters):
        toks = parse_dp(data, cfg, cm, mcache)
        S, est = stats_from(data, toks, cfg)
        try:
            blob = encode(data, toks, cfg)
            ok = decode(blob, len(data), cfg) == data
        except AssertionError:
            ok = False
        if verbose: print('  pasada', it, 'estimado', int(est), 'real', len(blob) if ok else 'FALLA')
        if ok and (best is None or len(blob) < len(best)): best = blob
        cm = CostModel(S)
    assert best is not None, 'no se pudo comprimir'
    assert decode(best, len(data), cfg) == data
    return best

if __name__ == '__main__':
    import sys
    d = open(sys.argv[1], 'rb').read()
    for once in [True, False]:
        for tree in [False, True]:
            c = Cfg(); c.NORM_ONCE = once; c.LOWTREE = tree
            b = compress(d, c, verbose=False)
            print('norm_once', once, 'lowtree', tree, len(d), '->', len(b), 'probs', layout(c)['N'])
