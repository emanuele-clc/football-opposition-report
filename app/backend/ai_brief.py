"""Coach brief written by a LOCAL language model (Ollama), from the hints of the game plan only. Optional: without Ollama the app keeps the
brief written by fixed templates (gameplan.brief).

Why local: no data leaves the machine (StatsBomb non-commercial licence, club data later) and no cost per brief.
Setup (once): install Ollama (https://ollama.com), then `ollama pull qwen2.5:3b`. Other model: OPPREPORT_AI_MODEL; other address: OLLAMA_URL.

Rules (fixed before the first run; the model only rewrites, it never adds):
- Input: the hints that fired (title, why, where to look, the numbers with rank and evidence grade) and the opponent's formations. Nothing else.
- Output: JSON, one sentence per hint (title and where to look, nothing added), each tied to the hint id it rewrites, so the app shows that
  hint's grade next to it. No free summary: in the first trial (3 Nov 2026, qwen2.5:3b) the summary is where the model added advice not in the hints.
- Check: every number in the model's text must appear in the facts it was given (decimal comma or dot, with or without %). A point with an
  unknown number is dropped. If no point survives, the app falls back to the template brief.
- English only (decided 3 Nov 2026): qwen2.5:3b wrote poor Italian and German in the first trial, worse than the app's dictionary, so the
  brief is always in English whatever the interface language.
- temperature 0.2 and a fixed seed, so the same facts give the same text with the same model; results cached in <data>/app_cache.
Not tested with analysts: a different wording of the same hints, not advice that wins matches.
"""

import hashlib, json, os, re, urllib.error, urllib.request

URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("OPPREPORT_AI_MODEL", "qwen2.5:3b")
LANG = {"en": "English", "it": "Italian", "de": "German"}
NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _call(path, body=None, timeout=5):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def status():
    """Is Ollama running, and is the model pulled?"""
    try:
        names = [m["name"] for m in _call("/api/tags").get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return {"available": False, "model": MODEL, "reason": "ollama_not_running"}
    ok = any(n == MODEL or n.split(":")[0] == MODEL or n == f"{MODEL}:latest" for n in names)
    return {"available": ok, "model": MODEL, "reason": None if ok else "model_not_pulled"}


def _fmt(v, unit):
    if unit == "pct":
        return f"{100 * v:.0f}%"
    return f"{v:.2f}" if unit == "num2" else f"{v:.1f}"


def facts(plan):
    """The only text the model sees: one block per hint, plus formations."""
    opp, mine = plan["opponent"], plan.get("mine")
    lines = [f"Opponent: {opp}." + (f" Your team: {mine}." if mine else "")]
    fo = plan.get("formations", {}).get("opponent")
    if fo and fo.get("most_used"):
        lines.append("Opponent formations: " + ", ".join(f"{f['formation']} in {f['matches']} of {fo['matches']} matches" for f in fo["most_used"][:3]) + ".")
    for h in plan["hints"]:
        ev = []
        for e in h["evidence"]:
            who = (mine if e.get("team") == "you" else opp) if e.get("team") else opp
            ev.append(f"{who}: {e['label']} {_fmt(e['value'], e['unit'])}, rank {e['rank']} of {e['of']}, grade {e.get('grade') or 'none'}")
        lines.append(f"[{h['id']}] {h['title']}. Why: {h['why']} Where to look: {h['look']} Numbers: {'; '.join(ev)}.")
    return "\n".join(lines)


def _nums(text):
    out = set()
    for m in NUM.findall(text):
        v = m.replace(",", ".")
        try:
            out.add(float(v))
        except ValueError:
            pass
    return out


def check(text, allowed):
    """Numbers in the text that are not in the facts."""
    return sorted(n for n in _nums(text) if n not in allowed)


SYSTEM = (
    "You rewrite hints for a football coach. For each hint, write ONE short sentence that says the same thing as its title and its "
    "'Where to look' part, in plain words. Do NOT add anything: no new numbers, players, tactics, set pieces, crosses, predictions or advice "
    "that the hint does not say. Never say something will work or win. You may keep one number of the hint, exactly as written. "
    "Write every sentence in {lang} only, even though the facts are in English. "
    "Answer in JSON: {{\"points\": [{{\"hint\": the hint id in brackets, \"text\": the sentence in {lang}}}]}}, one point per hint, "
    "in the order given, at most 5."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "points": {"type": "array", "items": {"type": "object", "properties": {"hint": {"type": "string"}, "text": {"type": "string"}},
                                              "required": ["hint", "text"]}},
    },
    "required": ["points"],
}


def write(plan, lang, cache_dir):
    """Brief by the local model, checked; None fields when nothing survives. Cached by model, language and facts."""
    st = status()
    if not st["available"]:
        return {**st, "summary": None, "points": [], "dropped": 0}
    if not plan["hints"]:
        return {**st, "summary": None, "points": [], "dropped": 0, "reason": "no_hints"}
    lang = "en"  # English only, see the header
    f = facts(plan)
    key = hashlib.sha256(f"{MODEL}|{lang}|{SYSTEM}|{f}".encode()).hexdigest()[:20]
    path = os.path.join(cache_dir, f"ai_brief_{key}.json")
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    body = {
        "model": MODEL,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0.2, "seed": 0},
        "messages": [
            {"role": "system", "content": SYSTEM.format(lang=LANG[lang])},
            {"role": "user", "content": f"Facts:\n{f}\n\nNow write the JSON. Every sentence in {LANG[lang]}; team names stay as they are."},
        ],
    }
    try:
        out = json.loads(_call("/api/chat", body, timeout=300)["message"]["content"])
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return {**st, "available": False, "reason": "model_failed", "summary": None, "points": [], "dropped": 0}
    allowed = _nums(f)
    ids = {h["id"]: h for h in plan["hints"]}
    points, dropped, seen = [], 0, set()
    for p in out.get("points", [])[:5]:
        hid = str(p.get("hint", "")).strip("[] ")
        text = str(p.get("text", "")).strip()
        if hid not in ids or hid in seen or not text or check(text, allowed):
            dropped += 1
            continue
        seen.add(hid)
        points.append({"hint": hid, "text": text, "grade": ids[hid].get("grade"), "tab": ids[hid]["tab"]})
    res = {**st, "lang": lang, "summary": None, "points": points, "dropped": dropped}
    if points:
        os.makedirs(cache_dir, exist_ok=True)
        json.dump(res, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return res
