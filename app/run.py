"""Start the opposition report app on http://127.0.0.1:8765
    python -X utf8 app/run.py                                  # the example teams in examples/
    python -X utf8 app/run.py --data-dir C:\\Users\\ecole\\sbdata  # every team the pipeline has processed there
Build the frontend once first: cd app/frontend; npm install; npm run build"""
import argparse, os, sys, webbrowser, threading
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--data-dir", help="folder with report_<Team>.json and the other pipeline outputs (default: examples/)")
ap.add_argument("--port", type=int, default=8765); ap.add_argument("--no-browser", action="store_true"); a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
if a.data_dir:
    if not os.path.isdir(a.data_dir): sys.exit(f"Data folder not found: {a.data_dir}")
    os.environ["OPPREPORT_DATA"] = os.path.abspath(a.data_dir)
if not os.path.exists(os.path.join(here, "frontend", "dist", "index.html")):
    sys.exit("Frontend not built. Run:  cd app/frontend; npm install; npm run build")
sys.path.insert(0, os.path.join(here, "backend"))
import uvicorn
from server import app, DATA
url = f"http://127.0.0.1:{a.port}"
print(f"Data: {DATA}\nOpen {url}  (Ctrl+C to stop)")
if not a.no_browser: threading.Timer(1.2, lambda: webbrowser.open(url)).start()
uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="warning")
