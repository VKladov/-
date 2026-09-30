"""What changed between two versions of the drawing.

Usage:
    node dwg2json.mjs new.dwg build/db_new.json
    python3 compare.py build/db.json build/db_new.json
"""
import json
import math
import sys

LAYERS = ('Электрика розетки', 'Освещение_выключатели', 'Стены')


def key(e):
    if e['type'] == 'LINE':
        s, t = e['startPoint'], e['endPoint']
        return (round(s['x'], 4), round(s['y'], 4), round(t['x'], 4), round(t['y'], 4))
    if e['type'] == 'LWPOLYLINE':
        return tuple((round(v['x'], 4), round(v['y'], 4)) for v in e['vertices'])
    return None


def describe(e):
    if e['type'] == 'LINE':
        s, t = e['startPoint'], e['endPoint']
        L = math.dist((s['x'], s['y']), (t['x'], t['y']))
        return (f"LINE  {e['layer']:22} цвет {e.get('colorIndex')}  ({s['x']:.3f}; {s['y']:.3f}) -> "
                f"({t['x']:.3f}; {t['y']:.3f})  L={L:.3f}")
    pts = ' '.join(f"({v['x']:.3f}; {v['y']:.3f})" for v in e['vertices'])
    return f"PLINE {e['layer']:22} цвет {e.get('colorIndex')}  {pts}"


def main(old_path, new_path):
    old = json.load(open(old_path)); new = json.load(open(new_path))
    A = {e['handle']: e for e in old['entities'] if e['layer'] in LAYERS and e['type'] in ('LINE', 'LWPOLYLINE')}
    B = {e['handle']: e for e in new['entities'] if e['layer'] in LAYERS and e['type'] in ('LINE', 'LWPOLYLINE')}
    added = [B[h] for h in B if h not in A]
    removed = [A[h] for h in A if h not in B]
    changed = [(A[h], B[h]) for h in A if h in B and
               (key(A[h]) != key(B[h]) or A[h].get('colorIndex') != B[h].get('colorIndex') or A[h]['layer'] != B[h]['layer'])]
    print(f'Добавлено: {len(added)}')
    for e in added:
        print('  +', describe(e))
    print(f'Удалено: {len(removed)}')
    for e in removed:
        print('  -', describe(e))
    print(f'Изменено: {len(changed)}')
    for a, b in changed:
        print('  было ', describe(a))
        print('  стало', describe(b))
    la = {l['name']: l.get('off') for l in old['tables']['LAYER']['entries']}
    for l in new['tables']['LAYER']['entries']:
        if la.get(l['name']) != l.get('off'):
            print(f"Слой «{l['name']}»: {'выключен' if l.get('off') else 'включён'}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
