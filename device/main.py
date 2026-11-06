# Presto entry point: copy device/ contents (main.py, gallery/, lib/) and web/ to the board root.
import sys

sys.path.append("/lib")

from gallery.l5_app import run  # noqa: E402

run()
