#!/usr/bin/env python3
"""Show the new end-of-player-data fields in Valheim .fch files (character version 47+).
Usage: python3 fch_tail.py save1.fch [save2.fch ...]

Layout (inferred from samples, not documented by Iron Gate):
  file    = [u32 payloadLen][payload][u32 64][sha512(payload)]
  payload ends with:
     build-menu blob = [u32 L][ [u32 n][n x (u32 len + name)][u32 0][u32 0] ]
     list A: [u32 a][a x (u32 key, u32 value)]   <- looks like pseudo-drop counters
     list B: [u32 b][b x 8 bytes]                <- grows by one per Forge attempt
"""
import hashlib, struct, sys

def u32(p, o): return struct.unpack_from('<I', p, o)[0]

def parse(p):
    # find the build-menu blob: its length prefix must match, and its contents must parse exactly
    for i in range(len(p) - 12, max(len(p) - 200000, 0), -1):
        L = u32(p, i)
        end = i + 4 + L
        if L < 12 or end > len(p) or len(p) - end > 65536: continue
        try:
            cnt = u32(p, i + 4); o = i + 8
            if cnt > 2000: continue
            for _ in range(cnt):
                ln = u32(p, o)
                if ln > 100: raise ValueError
                o += 4 + ln
            o += 4
            sc = u32(p, o); o += 4
            if sc > 2000: continue
            for _ in range(sc):
                ln = u32(p, o)
                if ln > 100: raise ValueError
                o += 8 + ln
            if o != end: continue
            a_o = end
            a = u32(p, a_o); o = a_o + 4 + a * 8
            b = u32(p, o); o += 4 + b * 8
            if o == len(p): return cnt, a_o
        except (ValueError, struct.error):
            continue
    return None

for path in sys.argv[1:]:
    x = open(path, 'rb').read()
    n = u32(x, 0)
    p = x[4:4 + n]
    ok = hashlib.sha512(p).digest() == x[8 + n:8 + n + 64]
    ver = u32(p, 0)
    print(f'{path}: version={ver} sha512_ok={ok}')
    if ver < 47:
        print('  (pre-1.0.20 format, no new fields)'); continue
    r = parse(p)
    if r is None:
        print('  layout not recognised'); continue
    cnt, o = r
    a = u32(p, o); o += 4
    print(f'  build-menu pieces={cnt}')
    print(f'  list A (pseudo-drop counters?) entries={a}')
    for _ in range(a):
        print(f'    key={u32(p,o):#010x}  value={u32(p,o+4)}'); o += 8
    b = u32(p, o); o += 4
    print(f'  list B (one per Forge attempt?) entries={b}')
    for _ in range(b):
        print(f'    {p[o:o+8].hex(" ")}   u32 pair=({u32(p,o):#010x}, {u32(p,o+4):#010x})'); o += 8
