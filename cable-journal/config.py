"""Settings shared by all steps."""
import os
from decimal import Decimal, ROUND_HALF_UP

# Drop heights, m (given by the customer). One drop per item.
DROPS = {
    'panel': 2.31,       # up from the panel, for every line leaving it
    'socket': 2.72,      # down to every socket
    'switch': 2.11,      # down to every switch
    'luminaire': 1.5,    # from every box that is a luminaire (square with a diagonal)
}
LENGTH_FACTOR = 1.1      # coefficient applied to every length (trace and drops), given by the customer;
                         # it is built into the numbers and not mentioned in the journal

# Cable per system: (brand, cores x section). Not given on the drawing - typical values.
CABLES = {
    'Розеточная сеть': ('ВВГнг(А)-LS', '3×2,5'),
    'Кондиционеры': ('ВВГнг(А)-LS', '3×2,5'),
    'Рабочее освещение': ('ВВГнг(А)-LS', '3×1,5'),
    'Аварийное освещение': ('ВВГнг(А)-FRLS', '3×1,5'),
}

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get('BUILD_DIR', os.path.join(HERE, 'build'))
DWG_JSON = os.environ.get('DWG_DB', os.path.join(BUILD, 'db.json'))
GROUPS_JSON = os.environ.get('GROUPS_FILE', os.path.join(BUILD, 'groups.json'))
NOTES_JSON = os.environ.get('NOTES', os.path.join(HERE, 'notes.json'))


def fmt_num(x):
    """2.31 -> '2,31', 1.5 -> '1,5'."""
    return ('%g' % x).replace('.', ',')


def r2(x):
    """Round to 0.01 half up, as Excel does."""
    return float(Decimal(repr(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def cable_length(g):
    """Cable length of a line as in the journal: trace and each kind of drops multiplied by LENGTH_FACTOR,
    rounded to 0.01 m."""
    drops = sum(r2(g[n] * DROPS[k] * LENGTH_FACTOR)
                for n, k in (('n_panel', 'panel'), ('n_sock', 'socket'), ('n_sw', 'switch'), ('n_lum', 'luminaire')))
    return r2(r2(g['horiz'] * LENGTH_FACTOR) + drops)
