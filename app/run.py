"""Start the opposition report app on http://127.0.0.1:8765
    python -X utf8 app/run.py                                  # the example teams in examples/
    python -X utf8 app/run.py --data-dir <data_folder>  # every team the pipeline has processed there
    python -X utf8 app/run.py --wyscout-dir <folder>    # second provider (Wyscout); default examples_wyscout/ if present
Build the frontend once first: cd app/frontend; npm install; npm run build"""

import argparse, os, sys, webbrowser, threading

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data-dir", help="folder with report_<Team>.json and the other pipeline outputs (default: examples/)")
ap.add_argument("--wyscout-dir", help="folder with the Wyscout reports (default: examples_wyscout/ if present)")
ap.add_argument("--port", type=int, default=8765)
ap.add_argument("--no-browser", action="store_true")
ap.add_argument(
    "--lan",
    action="store_true",
    help="also reachable from other devices on the same network (staff tablets); no login, use only on a trusted network",
)
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
if a.data_dir:
    if not os.path.isdir(a.data_dir):
        sys.exit(f"Data folder not found: {a.data_dir}")
    os.environ["OPPREPORT_DATA"] = os.path.abspath(a.data_dir)
if a.wyscout_dir:
    if not os.path.isdir(a.wyscout_dir):
        sys.exit(f"Wyscout folder not found: {a.wyscout_dir}")
    os.environ["OPPREPORT_DATA_WYSCOUT"] = os.path.abspath(a.wyscout_dir)
if not os.path.exists(os.path.join(here, "frontend", "dist", "index.html")):
    sys.exit("Frontend not built. Run:  cd app/frontend; npm install; npm run build")
sys.path.insert(0, os.path.join(here, "backend"))
import uvicorn
from server import app, PROVIDERS

url = f"http://127.0.0.1:{a.port}"
print("\n".join(f"Data ({p['name']}): {p['dir']}" for p in PROVIDERS.values()) + f"\nOpen {url}  (Ctrl+C to stop)")
if not a.no_browser:
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
host = "0.0.0.0" if a.lan else "127.0.0.1"
if a.lan:
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "<this computer's IP>"
    print(
        f"LAN mode: tablets and laptops on the same Wi-Fi can open http://{ip}:{a.port}  (only on a network you trust: there is no login)"
    )
uvicorn.run(app, host=host, port=a.port, log_level="warning")
