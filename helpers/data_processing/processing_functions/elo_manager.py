"""Compatibility alias for the legacy Elo manager import path."""

import sys

from data_processing.helpers.processing_functions import elo_manager as _elo_manager

sys.modules[__name__] = _elo_manager
