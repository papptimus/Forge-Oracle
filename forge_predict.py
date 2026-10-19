#!/usr/bin/env python3
"""Predict Valheim 1.0.20 Forge of Potential upgrades from a character save.

Usage:
  python forge_predict.py --item Hammer --level 3 --fch Yleinen.fch
  python forge_predict.py --item Hammer --level 3 --name Thor          (no save file)

  --item   item prefab name (Hammer, Hoe, AxeIron, SwordIron ...): the internal name, not the display name
  --level  the item's CURRENT level. Row 1 is current -> +1, row 2 is +1 -> +2, and so on.
  --fch    character save (.fch). Seeds already stored there are used, and the character name is read from it.
  --name   character name. Only needed without --fch, or if the name could not be read from the save.
  --count  how many upgrade steps to list (default 10)

Each level has its own saved seed, so each row uses the next roll for that level. Rows after the first
assume every earlier step succeeded, because a failed upgrade breaks the item.

How it works (read out of assembly_valheim.dll, Player.GetItemUpgradeChance):
  key  = hash(item) + target level
  seed = saved seed for key, else hash(character name) + key
  Random.InitState(seed); roll = Random.value; next_seed = Random.Range(0, 99999999)
"""
import argparse, hashlib, re, struct, sys
M = 0xFFFFFFFF; A = 1812433253
OK_NAME = re.compile(rb"[A-Za-z0-9 _\-']+")

def stable_hash(s):
    n = 5381; n2 = n
    for i in range(0, len(s), 2):
        n = ((((n << 5) + n) & M) ^ ord(s[i])) & M
        if i == len(s) - 1: break
        n2 = ((((n2 << 5) + n2) & M) ^ ord(s[i + 1])) & M
    return (n + (n2 * 1566083941)) & M

def roll_and_next(seed):
    x = seed & M; y = (x * A + 1) & M; z = (y * A + 1) & M; w = (z * A + 1) & M
    s = [x, y, z, w]
    def step():
        t = s[0] ^ ((s[0] << 11) & M); s[0], s[1], s[2] = s[1], s[2], s[3]
        s[3] = ((s[3] ^ (s[3] >> 19)) ^ (t ^ (t >> 8))) & M; return s[3]
    r1 = step(); r2 = step()
    return (r1 & 0x7FFFFF) / 8388607.0, r2 % 99999999

def u32(p, o): return struct.unpack_from('<I', p, o)[0]

def load(path):
    x = open(path, 'rb').read(); n = u32(x, 0); p = x[4:4 + n]
    if hashlib.sha512(p).digest() != x[8 + n:8 + n + 64]:
        print('warning: save checksum mismatch (file may be damaged or edited)', file=sys.stderr)
    return p

def read_slots(p):
    if u32(p, 0) < 47: return {}
    for i in range(len(p) - 12, max(len(p) - 200000, 0), -1):
        L = u32(p, i); end = i + 4 + L
        if L < 12 or end > len(p) or len(p) - end > 65536: continue
        try:
            cnt = u32(p, i + 4); o = i + 8
            if cnt > 2000: continue
            for _ in range(cnt):
                ln = u32(p, o)
                if ln > 100: raise ValueError
                o += 4 + ln
            o += 4                      # one u32 (always 0 so far)
            sc = u32(p, o); o += 4      # crafting stations: name + u32 each
            if sc > 2000: continue
            for _ in range(sc):
                ln = u32(p, o)
                if ln > 100: raise ValueError
                o += 8 + ln
            if o != end: continue
            a = u32(p, end); o = end + 4 + a * 8
            b = u32(p, o); o += 4
            if o + b * 8 != len(p): continue
            return {u32(p, o + 8 * k): u32(p, o + 8 * k + 4) for k in range(b)}
        except (ValueError, struct.error):
            continue
    return {}

def detect_name(p):
    """The character name is the string stored next to the character ID most often (crafter tags on items)."""
    seen = {}
    for i in range(8, len(p) - 10):
        L = p[i]
        if not 3 <= L <= 20 or i + 1 + L + 8 > len(p): continue
        s = p[i + 1:i + 1 + L]
        if not OK_NAME.fullmatch(s): continue
        for idb in (p[i - 8:i], p[i + 1 + L:i + 9 + L]):
            if idb[4:] == b'\0\0\0\0' and idb[:4] != b'\0\0\0\0':
                seen.setdefault((s, idb), []).append(i)
    best = sorted(((len(v), -v[0], k[0]) for k, v in seen.items() if len(v) >= 2), reverse=True)
    return best[0][2].decode() if best else None

def classify(r):
    return 'SUCCESS' if r <= 0.65 else 'FAIL (item breaks)'

ap = argparse.ArgumentParser(description='Predict Forge of Potential upgrades from a Valheim character save.')
ap.add_argument('--item', required=True); ap.add_argument('--level', type=int, required=True)
ap.add_argument('--fch'); ap.add_argument('--name'); ap.add_argument('--count', type=int, default=10)
ap.add_argument('--search', action='store_true', help='search for character names that start the item on a long success streak')
ap.add_argument('--max-len', type=int, default=4, help='longest name to try when searching (default 4; 5 is slow)')
ap.add_argument('--names', help='text file with one candidate name per line, used instead of the generated names')
ap.add_argument('--top', type=int, default=10)
a = ap.parse_args()

if a.search:
    import itertools, string
    ih = stable_hash(a.item)
    def streak(nm, cap=40):
        hn = stable_hash(nm); n = 0
        while n < cap:
            key = (ih + a.level + 1 + n) & M
            if roll_and_next((hn + key) & M)[0] > 0.65: break
            n += 1
        return n
    if a.names:
        cands = (l.strip() for l in open(a.names, encoding='utf-8') if l.strip())
    else:
        L = string.ascii_lowercase
        cands = (c + ''.join(r) for n in range(3, a.max_len + 1) for c in string.ascii_uppercase for r in itertools.product(L, repeat=n - 1))
    best = []
    for nm in cands:
        k = streak(nm)
        if k >= (best[-1][0] if len(best) >= a.top else 1):
            best.append((k, nm)); best.sort(key=lambda t: -t[0]); best = best[:a.top]
    print(f'item={a.item}  starting at level {a.level}: names whose first rolls succeed in a row\n')
    print('streak  name')
    for k, nm in best: print(f'{k:>6}  {nm}')
    print('\nOnly works for a character that has never tried this item at those levels. Untested in game.')
    sys.exit()

slots = {}; name = a.name
if a.fch:
    p = load(a.fch); slots = read_slots(p)
    if not name:
        name = detect_name(p)
        if name: print(f'character name read from save: {name}')

print(f'item={a.item}  current level={a.level}\n')
print('step   upgrade    roll     prediction')
need_name = False
for n in range(1, a.count + 1):
    lv = a.level + n
    key = (stable_hash(a.item) + lv) & M
    if key in slots: seed = slots[key]; src = 'save'
    elif name: seed = (stable_hash(name) + key) & M; src = 'fresh'
    else: need_name = True; break
    roll, _ = roll_and_next(seed)
    print(f'{n:>4}   {lv - 1:>2} -> {lv:<3}  {roll:.4f}   {classify(roll)}' + ('' if src == 'save' else '   [no saved seed yet]'))
if need_name:
    sys.exit('\nThis level has no saved seed yet. Pass --name <character name> (it could not be read from the save).')
print('\nRows after the first assume every earlier step succeeded.')
