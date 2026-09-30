"""Trace every cable line from the panel and write build/groups.json for the journal and the scheme."""
import collections
import json
import math

import networkx as nx

import geom
from analyze import analyze
from config import CABLES, DROPS, GROUPS_JSON, RESERVE
from geom import pt_seg_dist
from rooms import room_of, rooms_display

ROOM_ORDER = ['Пом. 1', 'Пом. 2', 'Пом. 3', 'Пом. 4', 'Пом. 5', 'Пом. 6', 'Пом. 7', 'Пом. 8', 'Пом. 9', 'Пом. 10',
              'Коридор', 'С/у 1', 'С/у 2', 'С/у 3', 'С/у 4']
NOTE_V1 = ('Участок 4,73 м по коридору между точками (7,26; 19,68) и (11,99; 19,68) на чертеже не начерчен; '
           'учтён в длине по указанию заказчика.')
NOTE_AC = 'Спуск к кондиционерам не добавлен: внутренние блоки на плане стоят в середине помещений (потолочные).'
NOTE_EMERG = 'На чертеже между участками линии есть зазор 17 мм; участки объединены.'


def rkey(r):
    return ROOM_ORDER.index(r) if r in ROOM_ORDER else 99


def seg_list(G, sub):
    return [dict(a=G.nodes[u]['pos'], b=G.nodes[v]['pos'], h=d['h'], virtual=d['h'].startswith('V'),
                 dashed=d.get('dashed', False))
            for u, v, d in sub.edges(data=True) if d['h'] != 'att']


def pos(G, ns):
    return [G.nodes[n]['pos'] for n in ns]


def rooms_str(rs):
    return rooms_display(sorted(set(rs), key=rkey))


def line(des, system, end, consumers, g, G, dev, cls, n_panel=1, n_sock=0, n_sw=0, n_lum=0, note='', start='Щиток'):
    cable, cores = CABLES[system]
    return dict(des=des, system=system, start=start, end=end, consumers=consumers, cable=cable, cores=cores,
                horiz=round(g['length'], 2), n_panel=n_panel, n_sock=n_sock, n_sw=n_sw, n_lum=n_lum, note=note,
                segs=seg_list(G, g['sub']), dev=pos(G, dev), cls=cls)


def socket_lines():
    out = []
    Gs, sg = analyze(['sock'], ['sym6'])
    Gw, wg_all = analyze(['wc_sock'], ['sym6'])
    wg = [g for g in wg_all if not g['starts']]          # WC lines branching off a socket line
    wg_panel = [g for g in wg_all if g['starts']]        # WC lines fed from the panel
    parent_of = {}
    for g in wg:
        p = Gw.nodes[g['dangling'][0]]['pos']
        best = None
        for i, pg in enumerate(sg):
            for u, v, d in pg['sub'].edges(data=True):
                if d['h'] == 'att':
                    continue
                a, b = Gs.nodes[u]['pos'], Gs.nodes[v]['pos']
                dist, t = pt_seg_dist(p, a, b)
                if best is None or dist < best[0]:
                    best = (dist, i, u, v, t, a, b)
        _, i, u, v, t, a, b = best
        dl = nx.single_source_dijkstra_path_length(sg[i]['sub'], sg[i]['starts'][0], weight='length')
        t = max(0, min(1, t))
        parent_of[id(g)] = (i, min(dl[u] + t * math.dist(a, b), dl[v] + (1 - t) * math.dist(a, b)))

    rows = []
    for i, g in enumerate(sg):
        rooms = [room_of(q) for q in pos(Gs, g['sockets'] + g['csockets'])]
        main_room = collections.Counter(rooms).most_common(1)[0][0]
        rows.append((rkey(main_room), Gs.nodes[g['starts'][0]]['pos'][0], i, g, rooms))
    rows.sort(key=lambda r: (r[0], r[1]))
    n = 0
    for _, _, idx, g, rooms in rows:
        n += 1
        nsock, nc = len(g['sockets']), len(g['csockets'])
        cons = f'Розетки — {nsock} шт.' + (f'; потолочная розетка — {nc} шт. (без спуска)' if nc else '')
        out.append(line(f'Р{n}', 'Розеточная сеть', rooms_str(rooms), cons, g, Gs, g['sockets'] + g['csockets'],
                        'sock', n_sock=nsock, note=NOTE_V1 if g['virtual'] else ''))
        for wgg in wg:
            pi, Lp = parent_of[id(wgg)]
            if pi != idx:
                continue
            wrooms = [room_of(q) for q in pos(Gw, wgg['sockets'])]
            note = ('Линия санузла на чертеже начинается от линии Р%d у стены коридора. Если санузел питается '
                    'отдельной группой от щитка, добавьте %s м по трассе Р%d и спуск к щитку.'
                    % (n, ('%.2f' % Lp).replace('.', ','), n))
            out.append(line(f'Р{n}.1', 'Розеточная сеть', rooms_str(wrooms),
                            f'Розетки санузла — {len(wgg["sockets"])} шт.', wgg, Gw, wgg['sockets'], 'wc_sock',
                            n_panel=0, n_sock=len(wgg['sockets']), note=note,
                            start=f'Ответвление от линии Р{n} (у стены коридора)'))
    wc_rows = []
    for g in wg_panel:
        wrooms = [room_of(q) for q in pos(Gw, g['sockets'])]
        wc_rows.append((min(rkey(x) for x in wrooms), g, wrooms))
    for _, g, wrooms in sorted(wc_rows, key=lambda t: t[0]):
        n += 1
        out.append(line(f'Р{n}', 'Розеточная сеть', rooms_str(wrooms), f'Розетки санузлов — {len(g["sockets"])} шт.',
                        g, Gw, g['sockets'], 'wc_sock', n_sock=len(g['sockets'])))
    return out


def ac_lines():
    Ga, ag = analyze(['ac'], ['sym6'])
    rows = sorted(((min(rkey(room_of(q)) for q in pos(Ga, g['ac'])), g) for g in ag), key=lambda t: t[0])
    return [line(f'К{k}', 'Кондиционеры', rooms_str([room_of(q) for q in pos(Ga, g['ac'])]),
                 f'Кондиционеры — {len(g["ac"])} шт.', g, Ga, g['ac'], 'ac', note=NOTE_AC)
            for k, (_, g) in enumerate(rows, 1)]


def lighting_lines():
    out = []
    Gl, lg = analyze(['light'], ['switch'])
    rows = []
    for g in lg:
        if geom.marked_boxes:          # luminaires are boxes with a diagonal
            lum = [b for b in g['boxes'] if Gl.nodes[b]['h'] in geom.marked_boxes]
        else:                          # older drawings: the box nearest to each switch is a junction box
            jbs = set()
            for sw in g['switches']:
                dist = nx.single_source_dijkstra_path_length(g['sub'], sw, weight='length')
                bx = sorted((dist[b], b) for b in g['boxes'] if b in dist)
                if bx:
                    jbs.add(bx[0][1])
            lum = [b for b in g['boxes'] if b not in jbs]
        main_room = collections.Counter(room_of(q) for q in pos(Gl, lum)).most_common(1)[0][0]
        rows.append((rkey(main_room), g, main_room, lum))
    k = 0
    for _, g, room, lum in sorted(rows, key=lambda t: t[0]):
        k += 1
        nsw = len(g['switches'])
        cons = f'Светильники — {len(lum)} шт.' + (f'; выключатель — {nsw} шт.' if nsw else '')
        note = '' if nsw else 'Выключатель на чертеже не подключён — спуск к нему не учтён.'
        out.append(line(f'О{k}', 'Рабочее освещение', rooms_str([room]), cons, g, Gl, lum + g['switches'], 'light',
                        n_sw=nsw, n_lum=len(lum), note=note))
    Gwl, wlg = analyze(['wc_light'], ['switch'])
    rows = []
    for g in wlg:
        if geom.marked_boxes:
            ends = [b for b in g['boxes'] if Gwl.nodes[b]['h'] in geom.marked_boxes]
        else:
            ends = g['dangling'] + [b for b in g['boxes'] if room_of(Gwl.nodes[b]['pos']).startswith('С/у')]
        rooms = [room_of(q) for q in pos(Gwl, ends)]
        rows.append((min(rkey(x) for x in rooms), g, rooms, ends))
    for _, g, rooms, ends in sorted(rows, key=lambda t: t[0]):
        k += 1
        out.append(line(f'О{k}', 'Рабочее освещение', rooms_str(rooms),
                        f'Светильники санузлов — {len(ends)} шт.; выключатели — {len(g["switches"])} шт.',
                        g, Gwl, ends + g['switches'], 'wc_light', n_sw=len(g['switches']), n_lum=len(ends)))
    return out


def emergency_lines():
    Ge, eg = analyze(['emerg'], ['switch'])
    out = []
    for g in eg:
        lum = [b for b in g['boxes'] if (not geom.marked_boxes) or Ge.nodes[b]['h'] in geom.marked_boxes]
        out.append(line('АО1', 'Аварийное освещение', rooms_display(['Коридор', 'Пом. 6']),
                        f'Светильники аварийного освещения — {len(lum)} шт.', g, Ge, g['boxes'], 'emerg',
                        n_lum=len(lum), note=NOTE_EMERG if g['virtual'] else ''))
    return out


def length(g):
    drops = (g['n_panel'] * DROPS['panel'] + g['n_sock'] * DROPS['socket'] + g['n_sw'] * DROPS['switch']
             + g['n_lum'] * DROPS['luminaire'])
    return round((g['horiz'] + drops) * (1 + RESERVE), 2)


if __name__ == '__main__':
    groups = socket_lines() + ac_lines() + lighting_lines() + emergency_lines()
    json.dump(groups, open(GROUPS_JSON, 'w'), ensure_ascii=False, indent=1)
    for g in groups:
        print(f"{g['des']:6} {g['end'][:24]:24} {g['consumers'][:50]:50} трасса {g['horiz']:6.2f}  "
              f"итого {length(g):6.2f} м")
    print(f"ВСЕГО {sum(length(g) for g in groups):.2f} м, линий {len(groups)} -> {GROUPS_JSON}")
