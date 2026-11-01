"""Descompresor en PowerPC (cuerpo de un código C0 del Gecko). Mismo modelo que decode() de packer.py.
El gestor de códigos lo llama con r15 = dirección del cuerpo (mtlr r15; blrl) y al volver sigue leyendo códigos en
(r15 + r4 + 7) & ~7, donde r4 = tamaño del C0 en bytes. Al salir guardamos en RET la dirección donde el gestor
habría seguido (r15 + r4, el código siguiente a este C0) y ponemos r4 = LIST - r15, así que el gestor sigue con la
lista descomprimida (esté donde esté la lista de códigos del cargador, por encima o por debajo). La lista
descomprimida acaba con otro C0 pequeño (ret_c0_lines) que vuelve a RET: así los códigos que el usuario tenga
activados detrás de este siguen funcionando, y el F0 final es el del .gct.
Se tocan r0, r3, r4 (a propósito), r5, r9, r10, cr0, ctr y XER[CA]; r17..r31 se guardan en la pila y se restauran.
No se tocan r6..r8, r15, r16 ni cr1..cr7, que son el estado del gestor.

La tabla de probabilidades va en la pila: la zona TRK la pisa el menú al cargar un .dol, y si eso pasa a mitad de
descomprimir la copia se desbocaría. Tras descomprimir se
vuelve a comprobar la suma: si no cuadra (el .dol pisó la lista mientras tanto), no se ejecuta la lista este frame.
Registros: r31 = LIST, r30 = tabla de probabilidades (r1 + 0x60), r28 = 0 hasta descomprimir, r29 = puntero de lectura (último byte leído),
r28 = último byte escrito, r27 = último byte de la lista, r26 = code, r25 = range, r24 = KIND + 4*prev_copia, r23 = desplazamiento de la copia,
r22 = acumulador de bits, r21 = contador de num (sale siempre a 0; empieza en 0 tras inicializar la tabla),
r20 = base del número, r19 = contexto del literal, r18 = lr de num, r17 = lr del gestor."""
def decoder_asm(o, cfg, blob_off, list_addr, list_len, probs_addr, nprobs, ret_addr):
    # El rango empieza en 0x80000000 (sale gratis del lis de LIST).
    assert list_addr & 31 == 0 and list_len & 3 == 0 and probs_addr & 1 == 0 and not cfg.LOWTREE
    assert list_addr >> 16 == 0x8000 and list_addr & 0xffff < 0x8000 and cfg.RANGE0 == 0x80000000
    assert (o['KIND'], o['REP'], o['LOW']) == (304, 312, 313) and cfg.REPM
    FRAME = 0x60 + ((2*nprobs + 15) & ~15)    # tabla de probabilidades en la pila (no la pisa la carga del .dol)
    norm = "" if cfg.NORM_ONCE else "  b nrm\n"
    return f"""
  stwu 1,-{FRAME}(1)
  stmw 17,0x10(1)
  mflr 17
  lis 25,0x8000
  addi 31,25,{list_addr & 0xffff}
  li 28,0
ck0:
  li 3,0
  li 0,{list_len//4}
  mtctr 0
  addi 5,31,-4
ck:
  lwzu 0,4(5)
  srwi 9,0,26
  cmpwi 9,18
  beq ck2
  add 3,3,0
ck2:
  bdnz ck
  lwz 5,{blob_off}(15)
  cmpw 3,5
  beq ready
  cmpwi 28,0
  bne skip
  addi 30,1,0x60
  li 5,{1 << (cfg.PB-1)}
  li 21,{2*nprobs}
pinit:
  addic. 21,21,-2
  sthx 5,30,21
  bne pinit
  addi 29,15,{blob_off+4+4-1}
  lwz 26,{blob_off+4}(15)
  addi 28,31,-1
  addi 27,28,{list_len}
lit:
  li 22,1
  rlwinm 19,28,4,26,27
lb:
  cmpwi 22,16
  add 3,22,19
  blt l1
  addi 3,22,48
l1:
  bl bit
  cmpwi 22,256
  blt lb
  stbu 22,1(28)
  li 24,{o['KIND']}
mloop:
  cmplw 28,27
  bge mdone
  rlwinm 3,28,0,30,31
  add 3,3,24
  bl bit
  beq lit
  addi 3,24,{o['REP'] - o['KIND']}
  bl bit
  bne gotoff
  li 20,{o['OFF']}
  bl num
  li 3,{o['LOW']}
  bl bit
  li 3,{o['LOW'] + 1}
  bl bit
  addi 23,22,-3
gotoff:
  li 20,{o['LEN']}
  bl num
  mtctr 22
  subf 3,23,28
cp:
  lbzu 0,1(3)
  stbu 0,1(28)
  bdnz cp
  li 24,{o['KIND'] + 4}
  b mloop
num:
  mflr 18
nu:
  add 3,20,21
  addi 21,21,1
  bl bit
  bne nu
  li 22,1
nb:
  addic. 21,21,-1
  beq nend
  subf 3,21,20
  bl bit
  b nb
nend:
  mtlr 18
  blr
bit:
  slwi 3,3,1
  lhzx 5,30,3
  srwi 9,25,{cfg.PB}
  mullw 9,9,5
  subfc 10,9,26
  adde 22,22,22
  andi. 0,22,1
  bne one
  mr 25,9
  subfic 10,5,{1 << cfg.PB}
  srwi 10,10,{cfg.SH}
  add 5,5,10
  b bst
one:
  mr 26,10
  subf 25,9,25
  srwi 10,5,{cfg.SH}
  subf 5,10,5
bst:
  sthx 5,30,3
nrm:
  andis. 10,25,0xff00
  bne nok
  lbzu 10,1(29)
  slwi 25,25,8
  slwi 26,26,8
  or 26,26,10
{norm}nok:
  andi. 0,22,1
  blr
mdone:
fl:
  dcbst 0,28
  sync
  icbi 0,28
  addi 28,28,-32
  cmplw 28,31
  bge fl
  isync
  b ck0
ready:
  add 3,15,4
  stw 3,{ret_addr - list_addr}(31)
  subf 4,15,31
skip:
  mtlr 17
  lmw 17,0x10(1)
  addi 1,1,{FRAME}
  blr
"""

def list_sum(payload):
    """Suma de comprobación de la lista: todas las palabras salvo los saltos 'b' (opcode 18), porque el gestor
    escribe el salto de vuelta en la última palabra de cada C2. Si no cuadra (arranque, o un .dol cargado
    a trozos encima), se vuelve a descomprimir antes de leer la lista."""
    import struct
    t = 0
    for (w,) in struct.iter_unpack('>I', payload):
        if w >> 26 != 18: t = (t + w) & 0xffffffff
    return t.to_bytes(4, 'big')

def ret_c0_lines(ret_addr):
    """C0 del final de la lista descomprimida: el gestor sigue en *(RET), justo detrás del C0 grande."""
    assert ret_addr >> 16 == 0x8000 and ret_addr & 0xffff < 0x8000 and ret_addr & 3 == 0
    return ["C0000000 00000002",
            "3C808000 %08X" % (0x80840000 | (ret_addr & 0xffff)),    # lis r4,0x8000 ; lwz r4,RET(r4)
            "7C8F2050 4E800020"]                                    # subf r4,r15,r4 ; blr
