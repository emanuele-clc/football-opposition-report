"""Minutes played and sending-offs in one match, from the StatsBomb events.

Time is the real elapsed time of the match: each period counts from its own kick-off (StatsBomb clocks restart at 45:00, 90:00,
105:00), so stoppage time is counted once and second halves do not overlap with the first. The penalty shootout (period 5) is left out.
- a player is on the pitch from kick-off if in the 'Starting XI', or from the 'Substitution' event in which he is the replacement;
  he leaves at his own 'Substitution' or at his sending-off (red card or second yellow, in 'Foul Committed' or 'Bad Behaviour');
- 'Player Off' / 'Player On' (a player treated off the pitch for a moment) are ignored;
- data without a 'Starting XI' (e.g. the generic CSV of other providers) give no minutes: callers fall back to matches played.
Definitions fixed on 19 Nov 2026 before looking at any output."""

PERIOD_CLOCK = {1: 0, 2: 45 * 60, 3: 90 * 60, 4: 105 * 60}
RED = {"Red Card", "Second Yellow"}


def clock(e):
    return e["minute"] * 60 + e["second"]


def elapsed_fn(ev):
    """(function event -> elapsed seconds or None, match length in seconds)."""
    ends = {}
    for e in ev:
        p = e.get("period")
        if p in PERIOD_CLOCK:
            ends[p] = max(ends.get(p, 0), clock(e) - PERIOD_CLOCK[p])
    offset, acc = {}, 0
    for p in sorted(ends):
        offset[p] = acc
        acc += ends[p]

    def elapsed(e):
        p = e.get("period")
        return offset[p] + max(clock(e) - PERIOD_CLOCK[p], 0) if p in offset else None

    return elapsed, acc


def match_minutes(ev, team):
    """{'length': match seconds, 'players': {name: seconds on the pitch} for team, 'reds': [{'side', 'player', 't', 'minute'}],
    'even_until': elapsed seconds of the first sending-off (or the match length), 'has_lineup': bool}."""
    elapsed, length = elapsed_fn(ev)

    on, off, reds = {}, {}, []
    has_lineup = False
    for e in ev:
        t = e["type"]["name"]
        us = e["team"]["name"] == team
        if t == "Starting XI" and us:
            has_lineup = True
            for pl in e["tactics"]["lineup"]:
                on.setdefault(pl["player"]["name"], 0)
        if elapsed(e) is None:
            continue
        if t == "Substitution" and us:
            off.setdefault(e["player"]["name"], elapsed(e))
            on.setdefault(e["substitution"]["replacement"]["name"], elapsed(e))
        card = (e.get("foul_committed") or e.get("bad_behaviour") or {}).get("card", {}).get("name")
        if card in RED and "player" in e:
            reds.append({"side": "for" if us else "against", "player": e["player"]["name"], "t": elapsed(e), "minute": e["minute"]})
            if us:
                off.setdefault(e["player"]["name"], elapsed(e))
    players = {p: max(min(off.get(p, length), length) - s, 0) for p, s in on.items()}
    first_red = min((r["t"] for r in reds), default=length)
    return {"length": length, "players": players, "reds": reds, "even_until": first_red, "has_lineup": has_lineup}
