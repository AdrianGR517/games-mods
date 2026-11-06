"""Arma el .gct: cabecera + C0 (descompresor + magia + datos comprimidos) + goto + fin."""
import keystone, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from packer import Cfg, layout, compress, decode
from unpack_asm import decoder_asm, list_sum
ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC32 | keystone.KS_MODE_BIG_ENDIAN)
LIST = 0x80004180
def asm(src, addr=0):
    e, _ = ks.asm(src, addr); return bytes(e)
F0LINE = bytes.fromhex('F000000000000000')
PROBS = 0x80005990                     # la tabla va en la pila; esto solo marca el final de las variables
PROBS_END = 0x80005C88                 # (la tabla TRK es ceros hasta 0x80005D34 en los 4 .dol)
RET = 0x80005C88                       # dirección del código que sigue al C0 grande (la escribe el C0 cada vez)
def build(payload, cfg=None, blob=None):
    """C0 = descompresor + magia (primera palabra de la lista) + datos comprimidos + ceros de relleno hasta 8.
    Se recortan los últimos bytes de los datos solo si la descompresión sigue saliendo bien leyendo en su lugar los
    ceros de relleno y sin leer nada más allá (detrás puede haber cualquier otro código del usuario)."""
    cfg = cfg or Cfg(); o = layout(cfg)
    assert len(payload) % 4 == 0
    data = payload
    if blob is None: blob = compress(data, cfg)
    full = blob; best = None
    for cut in range(0, 8):
        cand = full[:len(full) - cut] if cut else full
        blob_off = 0
        for _ in range(4):
            dec = asm(decoder_asm(o, cfg, blob_off, LIST, len(payload), PROBS, o['N'], RET))
            assert len(dec) % 4 == 0
            if len(dec) == blob_off: break
            blob_off = len(dec)
        else: raise RuntimeError('no converge')
        body = dec + list_sum(payload) + cand
        pad = -len(body) % 8
        tail = cand + b'\0' * pad                   # lo único que el descompresor puede leer: datos + relleno
        info = {}
        # la última copia no puede pasarse del final (el descompresor solo mira el final entre símbolos)
        try: ok = decode(tail, len(data), cfg, info) == data and info['len'] == len(data) and info['maxread'] <= len(tail)
        except Exception: ok = False
        if not ok: continue
        body += b'\0' * pad
        if best is None or len(body) < len(best[0]): best = (body, len(dec), len(cand), cut)
    body, ndec, nblob, cut = best
    probs = PROBS
    assert probs + 2*o['N'] <= PROBS_END
    lines = bytes.fromhex('C0000000') + struct.pack('>I', len(body)//8) + body
    return lines, dict(decoder=ndec, blob=nblob, cut=cut, body=len(body), total=len(lines) + 16, probs='pila (%d B)' % (2*o['N']))
