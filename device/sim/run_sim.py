"""Run the DeviceApp on this computer: python device/sim/run_sim.py [port]

Uses the fake `presto` module, stores data in .sim-storage/gallery and writes the
emulated screen to .sim-storage/screen.png. Open http://localhost:<port>/ in a browser.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "device" / "sim"), str(ROOT / "device" / "lib"), str(ROOT / "device")]

import presto  # noqa: E402  (the fake one)
from gallery import l5_app  # noqa: E402

STORAGE = ROOT / ".sim-storage"


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    STORAGE.mkdir(exist_ok=True)
    presto.SCREEN_PATH = str(STORAGE / "screen.png")
    config = dict(l5_app.DEFAULT_CONFIG, port=port, webRoot=str(ROOT / "web"),
                  storageBase=str(STORAGE / "gallery"))
    print(f"simulator on http://localhost:{port}/  screen: {presto.SCREEN_PATH}")
    asyncio.run(l5_app.main_async(presto.Presto(), config))


if __name__ == "__main__":
    main()
