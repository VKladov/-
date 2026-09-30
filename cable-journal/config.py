"""Settings shared by all steps."""
import os

# Drop heights, m (given by the customer). One drop per item.
DROPS = {
    'panel': 2.31,       # up from the panel, for every line leaving it
    'socket': 2.72,      # down to every socket
    'switch': 2.11,      # down to every switch
    'luminaire': 1.5,    # from every box that is a luminaire (square with a diagonal)
}
RESERVE = 0.0            # extra length share for termination and slack, e.g. 0.10 = 10 %

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
