"""Compatibility alias for the legacy parsing-list import path."""

import sys

from utils.parsing import list as _list

sys.modules[__name__] = _list
