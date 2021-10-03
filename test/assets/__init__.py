"""Uses pathlib to make referencing test assets by path easier."""

import os
from pathlib import Path

_ASSETS_DIRECTORY = Path(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIRECTORY_PATH = str(_ASSETS_DIRECTORY)
