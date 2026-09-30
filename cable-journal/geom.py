"""Wiring geometry from the DWG dump: line segments and symbols (boxes, sockets, switches, AC units)."""
import json
import math

from config import DWG_JSON

db = json.load(open(DWG_JSON))

SOCK_L = 'Электрика розетки'
LIGHT_L = 'Освещение_выключатели'
PANEL = (7.106, 21.389, 7.959, 21.47)   # distribution board outline, drawing metres


def cls_of(e):
    """Line class by layer and colour (see the legend of the drawing)."""
    L, c = e['layer'], e.get('colorIndex', 256)
    if L == SOCK_L:
        return {256: 'sock', 94: 'sock', 130: 'wc_sock', 4: 'wc_sock', 180: 'ac', 6: 'sym6'}.get(c, f'sock?{c}')
    if L == LIGHT_L:
        return {256: 'light', 30: 'light', 175: 'wc_light', 3: 'emerg', 202: 'switch'}.get(c, f'light?{c}')
    return None


segs = []      # wiring line segments
symbols = []   # polylines: boxes / devices
for e in db['entities']:
    c = cls_of(e)
    if c is None:
        continue
    if e['type'] == 'LINE':
        if c == 'sym6':
            continue   # crosses of ceiling sockets
        s, t = e['startPoint'], e['endPoint']
        segs.append(dict(h=e['handle'], cls=c, a=(s['x'], s['y']), b=(t['x'], t['y']),
                         dashed=bool(e.get('lineType')), layer=e['layer']))
    elif e['type'] == 'LWPOLYLINE':
        P = [(v['x'], v['y']) for v in e['vertices']]
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        w, hgt = max(xs) - min(xs), max(ys) - min(ys)
        if c == 'sym6':
            kind = 'socket'
        elif c == 'switch':
            kind = 'switch'
        elif c == 'ac' and max(w, hgt) > 0.3:
            kind = 'ac_unit'
        else:
            kind = 'box'
        symbols.append(dict(h=e['handle'], cls=c, kind=kind, pts=P, bbox=(min(xs), min(ys), max(xs), max(ys)),
                            c=(sum(xs) / len(xs), sum(ys) / len(ys)), w=w, hgt=hgt, layer=e['layer']))


def seglen(s):
    return math.dist(s['a'], s['b'])


def pt_seg_dist(p, a, b):
    """Distance from p to segment a-b and the projection parameter t."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.dist(p, a), 0
    t = ((px - ax) * dx + (py - ay) * dy) / L2
    tc = max(0, min(1, t))
    return math.dist(p, (ax + tc * dx, ay + tc * dy)), t


def poly_dist(p, P, closed=True):
    n = len(P)
    rng = range(n) if closed else range(n - 1)
    return min(pt_seg_dist(p, P[i], P[(i + 1) % n])[0] for i in rng)


def in_bbox(p, bb, tol=0.0):
    return bb[0] - tol <= p[0] <= bb[2] + tol and bb[1] - tol <= p[1] <= bb[3] + tol


def _on_perimeter(p, y, tol=0.004):
    return poly_dist(p, y['pts'], closed=True) < tol


# A line from corner to corner inside a box is a symbol mark (luminaire diagonal), not wiring.
decor = []
_boxes = [y for y in symbols if y['kind'] == 'box']
for s_ in list(segs):
    L_ = seglen(s_)
    if L_ > 0.2:
        continue
    for y in _boxes:
        if _on_perimeter(s_['a'], y) and _on_perimeter(s_['b'], y) and L_ > 0.9 * max(y['w'], y['hgt']):
            decor.append((s_, y))
            break
_decor_ids = set(id(s_) for s_, _ in decor)
segs[:] = [s_ for s_ in segs if id(s_) not in _decor_ids]
marked_boxes = set(y['h'] for _, y in decor)   # boxes with a diagonal = luminaires
