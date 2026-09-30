"""Floor areas of rooms from the wall linework of the DWG dump (layer «Стены»)."""
import json
import math
import shapely
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import unary_union, polygonize_full
from config import DWG_JSON
from rooms import ROOM_NAMES

WALL_LAYER = 'Стены'
SNAP_TOL = 0.005          # m: closes hairline gaps between wall lines
LEGEND_Y = 12.05          # legend lives below this y

# a point inside every room (drawing coordinates, m)
ROOM_SEEDS = {
    'Пом. 1': (5.9, 25.0), 'Пом. 2': (9.4, 25.0), 'Пом. 3': (14.0, 25.5), 'Пом. 4': (22.0, 25.5),
    'Пом. 5': (28.8, 25.0), 'Пом. 6': (32.0, 20.6), 'Пом. 7': (9.3, 15.8), 'Пом. 8': (14.0, 16.0),
    'Пом. 9': (22.8, 15.8), 'Пом. 10': (28.0, 15.0), 'С/у 1': (17.2, 22.8), 'С/у 2': (19.8, 22.8),
    'С/у 3': (17.2, 18.0), 'С/у 4': (19.6, 18.0), 'Коридор': (15.0, 20.4),
}
ORDER = ['Пом. 1', 'Пом. 2', 'Пом. 3', 'С/у 1', 'С/у 2', 'Пом. 4', 'Пом. 5', 'Пом. 10', 'Пом. 9',
         'С/у 4', 'С/у 3', 'Пом. 8', 'Пом. 7', 'Коридор', 'Пом. 6']   # by room number, then corridor spaces


def wall_segments(db):
    segs, columns = [], []
    for e in db['entities']:
        if e['layer'] != WALL_LAYER or e.get('colorIndex', 256) != 256:
            continue
        if e['type'] == 'LINE':
            a = (e['startPoint']['x'], e['startPoint']['y']); b = (e['endPoint']['x'], e['endPoint']['y'])
            if a[1] < LEGEND_Y and b[1] < LEGEND_Y:
                continue
            if a != b:
                segs.append((a, b))
        elif e['type'] == 'LWPOLYLINE':
            P = [(v['x'], v['y']) for v in e['vertices']]
            if all(p[1] < LEGEND_Y for p in P):
                continue
            closed = bool(e.get('flag', 0) & 1)
            # an open 4-vertex outline with equal sides is a column drawn without the closing side
            if not closed and len(P) == 4:
                sides = [math.dist(P[i], P[(i + 1) % 4]) for i in range(4)]
                if max(sides) - min(sides) < 0.01:
                    closed = True
                    columns.append(Polygon(P))
            n = len(P)
            for i in range(n if closed else n - 1):
                segs.append((P[i], P[(i + 1) % n]))
    return segs, columns


def room_polygons(db):
    segs, columns = wall_segments(db)
    lines = unary_union(MultiLineString([LineString(s) for s in segs]))
    lines = unary_union(shapely.snap(lines, lines, SNAP_TOL))
    polys, dangles, cuts, invalid = polygonize_full(lines)
    faces = list(polys.geoms)
    rooms = {}
    for name, seed in ROOM_SEEDS.items():
        hit = [p for p in faces if p.contains(Point(seed))]
        if not hit:
            raise RuntimeError(f'room {name}: no closed outline around {seed}')
        rooms[name] = min(hit, key=lambda p: p.area)
    # a column inside a room is a hole of the room outline, so it is already excluded from the area
    col_in = {n: [c for c in columns if Polygon(rooms[n].exterior).contains(c.centroid)] for n in rooms}
    other = [p for p in faces if p.area > 0.5 and all(p is not r for r in rooms.values())
             and not any(abs(p.area - c.area) < 1e-6 for c in columns)]
    return rooms, col_in, other


if __name__ == '__main__':
    db = json.load(open(DWG_JSON))
    rooms, col_in, other = room_polygons(db)
    tot = 0
    for n in ORDER:
        a = rooms[n].area
        tot += a
        extra = f'  (колонна {sum(c.area for c in col_in[n]):.2f} м² исключена)' if col_in[n] else ''
        print(f'{ROOM_NAMES[n]:18} {a:7.2f} м²  holes={len(rooms[n].interiors)}{extra}')
    print(f'ИТОГО {tot:.2f} м²')
    for p in other:
        c = p.representative_point()
        print(f'other face area={p.area:.2f} at ({c.x:.2f},{c.y:.2f}) bbox={tuple(round(v, 2) for v in p.bounds)}')
