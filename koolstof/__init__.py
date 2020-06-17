"""Miscellaneous tools for marine carbonate chemistry."""

import numpy as np
from . import crm, vindta

__all__ = ["crm", "vindta"]


def sigfig(x, sf):
    """Return `x` to `sf` significant figures."""
    factor = 10.0 ** np.ceil(np.log10(np.abs(x)))
    return factor * np.around(x / factor, decimals=sf)
