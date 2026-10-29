import struct
class Dol:
  def __init__(s,p):
    d=open(p,'rb').read(); s.d=d
    off=struct.unpack('>18I',d[0:72]);addr=struct.unpack('>18I',d[72:144]);sz=struct.unpack('>18I',d[144:216])
    s.segs=[(addr[i],off[i],sz[i],i) for i in range(18) if sz[i]]
    s.bss=struct.unpack('>3I',d[216:228]); s.entry=s.bss[2]
  def rd(s,a,n):
    for va,o,z,i in s.segs:
      if va<=a<va+z: return s.d[o+a-va:o+a-va+n]
  def u32(s,a):
    b=s.rd(a,4); return struct.unpack('>I',b)[0] if b else None
  def find(s,b):
    r=[]
    for va,o,z,i in s.segs:
      k=s.d.find(b,o,o+z)
      while k>=0: r.append(va+k-o); k=s.d.find(b,k+1,o+z)
    return r
