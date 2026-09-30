"""Split the wiring of each class into lines (connected components without the panel)."""
import collections

import networkx as nx

import geom
from graph import build
from rooms import room_of

# ---- corrections to the drawing ---------------------------------------------------------
# (class, start, end, id, why)
VIRTUAL = [
    ('sock', (7.262, 19.679), (11.989, 19.679), 'V1',
     'Р11: участок 4,73 м по коридору на чертеже не начерчен, учитывается по указанию заказчика.'),
    ('emerg', (31.394, 20.112), (31.394, 20.129), 'V2',
     'АО1: зазор 17 мм между участками линии на чертеже.'),
]
for cls, a, b, h, note in VIRTUAL:
    geom.segs.append(dict(h=h, cls=cls, a=a, b=b, dashed=False, layer='virtual', note=note))


def dedupe(G):
    """Merge symbols drawn twice at the same place."""
    seen = {}
    for n in list(G.nodes):
        d = G.nodes[n]
        if d['kind'] in ('box', 'socket', 'switch', 'ac_unit'):
            key = (d['kind'], round(d['pos'][0], 3), round(d['pos'][1], 3))
            if key in seen:
                for m in list(G.neighbors(n)):
                    G.add_edge(m, seen[key], key='att', length=0.0, h='att', cls='att')
                G.remove_node(n)
            else:
                seen[key] = n
    return G


def is_ceiling_socket(d):
    bb = d['bbox']
    return abs(bb[2] - bb[0] - 0.1) < 0.005 and abs(bb[3] - bb[1] - 0.1) < 0.005


def analyze(classes, extra):
    G, S, syms, nodes, tj = build(classes, extra_symbol_classes=extra)
    G = dedupe(G)
    H = G.copy()
    H.remove_node('PANEL')
    H.remove_nodes_from([n for n in H.nodes if H.degree(n) == 0])
    groups = []
    for comp in nx.connected_components(H):
        sub = H.subgraph(comp)
        edges = [(u, v, d) for u, v, d in sub.edges(data=True) if d['h'] != 'att']
        kinds = collections.defaultdict(list)
        for n in comp:
            if G.nodes[n]['kind'] != 'pt':
                kinds[G.nodes[n]['kind']].append(n)
        handles = sorted(set(d['h'] for _, _, d in edges))
        groups.append(dict(
            cls=classes[0], comp=comp, sub=sub, G=G,
            length=sum(d['length'] for _, _, d in edges),
            starts=[n for n in comp if G.has_edge(n, 'PANEL')],
            sockets=[n for n in kinds['socket'] if not is_ceiling_socket(G.nodes[n])],
            csockets=[n for n in kinds['socket'] if is_ceiling_socket(G.nodes[n])],
            switches=kinds['switch'], boxes=kinds['box'], ac=kinds['ac_unit'],
            dangling=[n for n in comp if G.nodes[n]['kind'] == 'pt' and sub.degree(n) == 1
                      and not G.has_edge(n, 'PANEL')],
            handles=handles, virtual=[h for h in handles if h.startswith('V')],
        ))
    return G, groups


if __name__ == '__main__':
    # diagnostics: every line of every class
    cfg = [(['sock'], ['sym6']), (['wc_sock'], ['sym6']), (['ac'], ['sym6']),
           (['light'], ['switch']), (['wc_light'], ['switch']), (['emerg'], ['switch'])]
    for classes, extra in cfg:
        G, groups = analyze(classes, extra)
        print('=====', classes[0], len(groups))
        for g in sorted(groups, key=lambda g: -len(g['starts'])):
            rooms = collections.Counter(room_of(G.nodes[n]['pos'])
                                        for n in g['sockets'] + g['switches'] + g['ac'] + g['csockets'])
            print(f"  L={g['length']:.2f} from_panel={bool(g['starts'])} sock={len(g['sockets'])} "
                  f"sw={len(g['switches'])} box={len(g['boxes'])} ac={len(g['ac'])} "
                  f"loose_ends={len(g['dangling'])} rooms={dict(rooms)}")
