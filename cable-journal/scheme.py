"""PDF scheme of cable groups on the plan (3 pages). Usage: python3 scheme.py out.pdf"""
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

import label_offsets as LO
from config import GROUPS_JSON, cable_length
from geom import db, symbols, PANEL, decor
from rooms import ROOM_NAMES

plt.rcParams['font.family'] = 'DejaVu Sans'
groups = json.load(open(GROUPS_JSON))
for g in groups:
    g['total'] = cable_length(g)
PREVIEW_DIR = os.environ.get('PREVIEW_DIR')     # set to also save PNG previews of the pages

def fmt(x):
    return ('%.2f' % x).replace('.', ',')

XMIN, XMAX, YMIN, YMAX = 3.85, 34.45, 12.0, 28.15

def draw_walls(ax):
    for e in db['entities']:
        if e['layer'] not in ('Стены', 'перегородки'): continue
        if e['type'] == 'LINE':
            a, b = e['startPoint'], e['endPoint']
            if a['y'] < 12.05 and b['y'] < 12.05: continue
            ax.plot([a['x'], b['x']], [a['y'], b['y']], color='#9a9a9a', lw=0.6, zorder=1, solid_capstyle='butt')
        elif e['type'] == 'LWPOLYLINE':
            P = [(v['x'], v['y']) for v in e['vertices']]
            if all(p[1] < 12.05 for p in P): continue
            xs, ys = zip(*P)
            ax.plot(xs, ys, color='#9a9a9a', lw=0.6, zorder=1)

def draw_symbols(ax, kinds):
    for y in symbols:
        if y['kind'] not in kinds: continue
        if y['c'][1] < 12.05: continue  # legend
        P = y['pts'] + [y['pts'][0]]
        xs, ys = zip(*P)
        ax.plot(xs, ys, color='#444444', lw=0.5, zorder=3)
    for s_, y in decor:  # luminaire diagonal marks
        if y['c'][1] < 12.05: continue
        ax.plot([s_['a'][0], s_['b'][0]], [s_['a'][1], s_['b'][1]], color='#444444', lw=0.5, zorder=3)

ROOM_LABELS = {   # preferred label positions; the final position is the nearest spot free of lines
    'Пом. 1': (5.95, 27.4), 'Пом. 2': (9.4, 27.4), 'Пом. 3': (13.35, 27.1), 'Пом. 4': (20.25, 27.25),
    'Пом. 5': (28.7, 27.28), 'Пом. 6': (31.25, 20.85), 'Пом. 7': (9.35, 13.45), 'Пом. 8': (13.0, 13.62),
    'Пом. 9': (20.3, 13.5), 'Пом. 10': (26.9, 13.35), 'С/у 1': (17.2, 23.7), 'С/у 2': (19.8, 23.7),
    'С/у 3': (17.2, 17.1), 'С/у 4': (19.6, 17.1), 'Коридор': (5.6, 18.35),
}

LABEL_TEXT = {'Пом. 6': 'Тамбур\nкоридора'}


ROOM_LABEL_FS = 9.5
_M_PER_PT = (XMAX - XMIN) / (16.54 * 0.97 * 72)      # metres of drawing per typographic point on the page


def _label_box(text, x, y):
    lines = text.split('\n')
    w = max(len(l) for l in lines) * 0.6 * ROOM_LABEL_FS * _M_PER_PT + 0.1
    h = len(lines) * 1.25 * ROOM_LABEL_FS * _M_PER_PT + 0.06
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _seg_hits_box(a, b, box):
    x0, y0, x1, y1 = box
    # Liang-Barsky clipping: does segment a-b touch the rectangle?
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _obstacles():
    obs = []
    for g in groups:
        for sg in g['segs']:
            obs.append((tuple(sg['a']), tuple(sg['b'])))
    for y in symbols:
        if y['kind'] in ('socket', 'switch', 'ac_unit', 'box'):
            P = y['pts'] + [y['pts'][0]]
            obs += [(P[i], P[i + 1]) for i in range(len(P) - 1)]
    return obs


def _place_room_labels():
    from rooms import ROOMS, pip
    polys = dict(ROOMS)
    obs = _obstacles()
    placed = {}
    for name, (x0, y0) in ROOM_LABELS.items():
        text = LABEL_TEXT.get(name, ROOM_NAMES.get(name, name))
        best = None
        for i in range(-15, 16):
            for j in range(-15, 16):
                x, y = x0 + i * 0.1, y0 + j * 0.1
                box = _label_box(text, x, y)
                corners = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
                if name in polys and not all(pip(c, polys[name]) for c in corners):
                    continue
                if any(_seg_hits_box(a, b, box) for a, b in obs):
                    continue
                d = math.hypot(x - x0, y - y0)
                if best is None or d < best[0]:
                    best = (d, x, y)
        placed[name] = (text, (best[1], best[2]) if best else (x0, y0))
    return placed


_ROOM_LABEL_POS = None


def draw_rooms(ax):
    global _ROOM_LABEL_POS
    if _ROOM_LABEL_POS is None:
        _ROOM_LABEL_POS = _place_room_labels()
    for name, (text, (x, y)) in _ROOM_LABEL_POS.items():
        ax.text(x, y, text, ha='center', va='center', fontsize=ROOM_LABEL_FS, color='#8a8a8a', style='italic', zorder=2,
                linespacing=1.0, bbox=dict(boxstyle='square,pad=0.1', facecolor='white', edgecolor='none', alpha=0.8))

def draw_panel(ax):
    x0, y0, x1, y1 = PANEL
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor='#222222', edgecolor='#222222', zorder=6))
    ax.annotate('Щиток', xy=((x0 + x1) / 2, y1), xytext=((x0 + x1) / 2 - 1.2, y1 + 0.9), fontsize=9, weight='bold',
                arrowprops=dict(arrowstyle='-', color='#222222', lw=0.8), zorder=7)

PALETTE = ['#1f77b4', '#d62728', '#2ca02c', '#9467bd', '#ff7f0e', '#17becf', '#8c564b', '#e377c2', '#bcbd22',
           '#7f7f7f', '#393b79', '#ad494a', '#637939', '#843c39', '#d6616b', '#3182bd', '#c51b8a', '#e6550d',
           '#756bb1', '#636363']

def page(pdf, title, sel, label_off=None, png=None):
    label_off = label_off or {}
    fig = plt.figure(figsize=(16.54, 11.69))
    ax = fig.add_axes([0.015, 0.225, 0.97, 0.69])
    ax.set_xlim(XMIN, XMAX); ax.set_ylim(YMIN, YMAX); ax.set_aspect('equal'); ax.axis('off')
    draw_walls(ax); draw_rooms(ax); draw_panel(ax)
    draw_symbols(ax, {'socket', 'switch', 'ac_unit', 'box'})
    colors = {}
    ci = 0
    for g in sel:
        base = g['des'].split('.')[0]
        if base not in colors:
            colors[base] = PALETTE[ci % len(PALETTE)]; ci += 1
        col = colors[base]
        branch = '.' in g['des']
        for s in g['segs']:
            (x1, y1), (x2, y2) = s['a'], s['b']
            ax.plot([x1, x2], [y1, y2], color=col, lw=1.3 if not branch else 1.1,
                    ls='-' if not branch else (0, (5, 2)), zorder=4, solid_capstyle='round')
        # label(s): per device for AC lines, otherwise one label at the devices' centroid
        if g['cls'] == 'ac':
            anchors = [tuple(p) for p in g['dev']]
        else:
            xs = [p[0] for p in g['dev']]; ys = [p[1] for p in g['dev']]
            anchors = [(sum(xs) / len(xs), sum(ys) / len(ys))]
        for k, (cx, cy) in enumerate(anchors):
            off = label_off.get(g['des'], (0, 0))
            dx, dy = off[k] if isinstance(off[0], (list, tuple)) else off
            ax.text(cx + dx, cy + dy, g['des'], ha='center', va='center', fontsize=10, weight='bold', color=col,
                    zorder=8, bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor=col, lw=1.2))
    fig.text(0.015, 0.972, title, fontsize=15, weight='bold')
    fig.text(0.015, 0.958, 'К кабельному журналу. Номера групп условные (на чертеже их нет), '
             'названия помещений — по данным заказчика.\nДлины кабеля — как в кабельном журнале.',
             fontsize=9.5, color='#333333', va='top')
    # legend table
    n = len(sel)
    ncol = 4 if n > 12 else 3
    per = math.ceil(n / ncol)
    for i, g in enumerate(sel):
        col = colors[g['des'].split('.')[0]]
        c, r = divmod(i, per)
        x = 0.02 + c * (0.96 / ncol); y = 0.2 - r * 0.0215
        fig.text(x, y, g['des'], fontsize=9.5, weight='bold', color=col, va='top')
        fig.text(x + 0.032, y, f"{g['end']} — {fmt(g['total'])} м", fontsize=9, va='top')
    if any('.' in g['des'] for g in sel):
        fig.text(0.985, 0.952, 'пунктир цвета группы — ответвление к розеткам санузла',
                 fontsize=9, color='#333333', ha='right')
    pdf.savefig(fig)
    if png and PREVIEW_DIR:
        fig.savefig(os.path.join(PREVIEW_DIR, png), dpi=110)
    plt.close(fig)

if __name__ == '__main__':
    out = sys.argv[1]
    sock = [g for g in groups if g['system'] == 'Розеточная сеть']
    ac = [g for g in groups if g['system'] == 'Кондиционеры']
    light = [g for g in groups if g['system'] in ('Рабочее освещение', 'Аварийное освещение')]
    with PdfPages(out) as pdf:
        page(pdf, 'Схема групп: розеточная сеть', sock, LO.SOCK, png='p1.png')
        page(pdf, 'Схема групп: кондиционеры', ac, LO.AC, png='p2.png')
        page(pdf, 'Схема групп: рабочее и аварийное освещение', light, LO.LIGHT, png='p3.png')
