"""Connectivity graph of wiring segments, symbols and the panel."""
import math

import networkx as nx

from geom import segs, symbols, PANEL, seglen, pt_seg_dist, in_bbox

TOL = 0.004   # m: endpoints closer than this are one node


def build(classes, extra_symbol_classes=()):
    """Graph of the wiring segments whose class is in `classes`."""
    S = [s for s in segs if s['cls'] in classes]
    syms = [y for y in symbols if (y['cls'] in classes or y['cls'] in extra_symbol_classes)]
    G = nx.MultiGraph()
    nodes = []

    def node_for(p):
        for i, q in enumerate(nodes):
            if math.dist(p, q) < TOL:
                return f'p{i}'
        nodes.append(p)
        return f'p{len(nodes) - 1}'

    for s in S:
        na, nb = node_for(s['a']), node_for(s['b'])
        G.add_edge(na, nb, key=s['h'], length=seglen(s), h=s['h'], cls=s['cls'], dashed=s['dashed'])
    for i, q in enumerate(nodes):
        G.nodes[f'p{i}']['pos'] = q
        G.nodes[f'p{i}']['kind'] = 'pt'
    for y in syms:
        G.add_node('S' + y['h'], pos=y['c'], kind=y['kind'], cls=y['cls'], bbox=y['bbox'], h=y['h'])
    # a line ending inside a symbol is connected to it
    for i, q in enumerate(nodes):
        for y in syms:
            if in_bbox(q, y['bbox'], TOL):
                G.add_edge(f'p{i}', 'S' + y['h'], key='att', length=0.0, h='att', cls='att')
    G.add_node('PANEL', pos=((PANEL[0] + PANEL[2]) / 2, (PANEL[1] + PANEL[3]) / 2), kind='panel')
    for i, q in enumerate(nodes):
        if in_bbox(q, PANEL, TOL):
            G.add_edge(f'p{i}', 'PANEL', key='att', length=0.0, h='att', cls='att')
    # endpoints lying on the middle of another segment (T-junctions) - reported for checking
    tj = []
    for i, q in enumerate(nodes):
        for s in S:
            d, t = pt_seg_dist(q, s['a'], s['b'])
            if d < TOL and 1e-6 < t < 1 - 1e-6 and math.dist(q, s['a']) > TOL and math.dist(q, s['b']) > TOL:
                tj.append((f'p{i}', q, s['h'], s['cls']))
    return G, S, syms, nodes, tj
