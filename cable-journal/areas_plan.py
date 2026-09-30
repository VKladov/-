"""One-page plan with room outlines and floor areas. Usage: python3 areas_plan.py out.pdf"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from areas import room_polygons, ORDER
from config import DWG_JSON
from rooms import ROOM_NAMES

plt.rcParams['font.family'] = 'DejaVu Sans'
XMIN, XMAX, YMIN, YMAX = 3.85, 34.45, 11.4, 28.25
LABEL_AT = {'С/у 1': (17.2, 22.75), 'С/у 2': (19.83, 22.75), 'С/у 3': (17.19, 18.0), 'С/у 4': (19.57, 18.0),
            'Коридор': (15.0, 20.42), 'Пом. 6': (31.95, 20.55), 'Пом. 10': (27.3, 15.6)}


def fmt(x):
    return ('%.2f' % x).replace('.', ',')


def main(out, png=None):
    db = json.load(open(DWG_JSON))
    rooms, col_in, other = room_polygons(db)
    fig = plt.figure(figsize=(16.54, 11.69))
    ax = fig.add_axes([0.015, 0.2, 0.97, 0.72])
    ax.set_xlim(XMIN, XMAX); ax.set_ylim(YMIN, YMAX); ax.set_aspect('equal'); ax.axis('off')
    for p in other:                                      # wall footprint
        xs, ys = p.exterior.xy
        ax.fill(xs, ys, color='#d9d9d9', zorder=1, lw=0)
        for h in p.interiors:
            xs, ys = h.xy
            ax.fill(xs, ys, color='white', zorder=1, lw=0)
    for n in ORDER:
        p = rooms[n]
        wc = n.startswith('С/у')
        face = '#dbeafe' if n.startswith('Пом') and n != 'Пом. 6' else ('#e0f2e9' if wc else '#fff4d6')
        xs, ys = p.exterior.xy
        ax.fill(xs, ys, color=face, zorder=2, lw=0)
        ax.plot(xs, ys, color='#4a4a4a', lw=0.8, zorder=3)
        for h in p.interiors:
            xs, ys = h.xy
            ax.fill(xs, ys, color='#9e9e9e', zorder=3, lw=0)
            ax.plot(xs, ys, color='#4a4a4a', lw=0.8, zorder=3)
        x, y = LABEL_AT.get(n, (p.representative_point().x, p.representative_point().y))
        if n not in LABEL_AT:
            c = p.centroid
            x, y = (c.x, c.y) if p.contains(c) else (x, y)
        name = ROOM_NAMES[n]
        if wc:
            name = name.replace(' ', '\n')
        ax.text(x, y, f'{name}\n{fmt(p.area)} м²', ha='center', va='center', fontsize=11 if not wc else 8.5,
                weight='bold', color='#1f2937', zorder=5, linespacing=1.15)
    fig.text(0.015, 0.965, 'Площади полов помещений', fontsize=16, weight='bold')
    fig.text(0.015, 0.945, 'Площадь — по внутреннему контуру стен на плане, без дверных проёмов; '
             'колонна в кабинете 1022 (0,45×0,45 м) исключена. Названия помещений — по данным заказчика.',
             fontsize=10, color='#333333', va='top')
    total = sum(rooms[n].area for n in ORDER)
    rows = [(ROOM_NAMES[n], rooms[n].area) for n in ORDER]
    ncol = 3; per = (len(rows) + ncol - 1) // ncol
    for i, (name, a) in enumerate(rows):
        c, r = divmod(i, per)
        x = 0.03 + c * 0.3; y = 0.175 - r * 0.024
        fig.text(x, y, name, fontsize=10.5, va='top')
        fig.text(x + 0.2, y, f'{fmt(a)} м²', fontsize=10.5, va='top', ha='right')
    fig.text(0.93, 0.175, f'Итого: {fmt(total)} м²', fontsize=12, weight='bold', va='top', ha='right')
    with PdfPages(out) as pdf:
        pdf.savefig(fig)
    if png:
        fig.savefig(png, dpi=110)
    plt.close(fig)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
