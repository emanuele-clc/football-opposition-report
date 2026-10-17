"""Reruns the descriptive sheets of the app (defending, matchups, key players) in an empty folder and checks the JSON files are identical
to the ones in the data folder. The raw events are linked, not copied.
Usage:  python -X utf8 tests/reproduce_sheets.py <data_folder>      (the folder with matches/, ev/ and the sheets of the 10 thesis teams)"""
import filecmp, os, shutil, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__)); rep = os.path.join(os.path.dirname(here), "src", "report")
data = os.path.abspath(sys.argv[1])
TEAMS = [("9_281", "Bayer Leverkusen"), ("2_27", "Leicester City"), ("11_27", "Barcelona"), ("2_27", "Arsenal"), ("11_27", "Atlético Madrid"),
         ("11_27", "Real Madrid"), ("12_27", "Napoli"), ("12_27", "Sassuolo"), ("7_27", "Gazélec Ajaccio"), ("7_27", "Bordeaux")]
tmp = tempfile.mkdtemp()


def link(src, dst):
    try:
        import _winapi; _winapi.CreateJunction(src, dst)
    except (ImportError, OSError):
        os.symlink(src, dst, target_is_directory=True)


link(os.path.join(data, "ev"), os.path.join(tmp, "ev")); link(os.path.join(data, "matches"), os.path.join(tmp, "matches"))
same = diff = 0
try:
    for mid, team in TEAMS:
        k = team.replace(" ", "_")
        for s in ("defending", "matchups", "keyplayers"):
            ref = os.path.join(data, f"{s}_{k}.json")
            if not os.path.exists(ref): print("missing", ref); diff += 1; continue
            subprocess.run([sys.executable, "-X", "utf8", os.path.join(rep, f"{s}.py"), os.path.join("matches", f"{mid}.json"), team, "."], cwd=tmp, capture_output=True)
            ok = filecmp.cmp(os.path.join(tmp, f"{s}_{k}.json"), ref, shallow=False) if os.path.exists(os.path.join(tmp, f"{s}_{k}.json")) else False
            same += ok; diff += not ok
            if not ok: print("DIFFERENT", f"{s}_{k}.json")
finally:
    for d in ("ev", "matches"): os.rmdir(os.path.join(tmp, d))  # removes the link only, never the linked folder
    shutil.rmtree(tmp)
print(f"{same}/{same + diff} identical")
sys.exit(1 if diff else 0)
