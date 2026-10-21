import { useEffect, useState } from "react";
import { api, type ClipRef, type ClipRow } from "./api";
import { clock } from "./format";

const cache = new Map<string, Promise<ClipRow[]>>();

/* Clip list rows for one team and list, fetched once per session. */
export function useClips(key: string, kind: string) {
  const [rows, setRows] = useState<ClipRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    const k = `${key}/${kind}`;
    if (!cache.has(k))
      cache.set(
        k,
        api.clips(key, kind).then((r) => r.rows),
      );
    setRows(null);
    setError(null);
    cache
      .get(k)!
      .then((r) => live && setRows(r))
      .catch((e) => {
        cache.delete(k);
        if (live) setError(String(e.message ?? e));
      });
    return () => {
      live = false;
    };
  }, [key, kind]);
  return { rows, error };
}

const goalCache = new Map<string, Promise<Set<string>>>();
export const clipId = (r: { match: number; half: number; minute: number; second: number }) =>
  `${r.match}-${r.half}-${r.minute}-${r.second}`;

/* Clips of one list that ended in a goal (read by the backend from the raw events), fetched once per session.
   null while loading or without event files: the goal filter is then hidden. */
export function useGoals(key: string, kind: string, events: boolean) {
  const [goals, setGoals] = useState<Set<string> | null>(null);
  useEffect(() => {
    setGoals(null);
    if (!events) return;
    let live = true;
    const k = `${key}/${kind}`;
    if (!goalCache.has(k))
      goalCache.set(
        k,
        api
          .clipGoals(key, kind)
          .then(
            (g) => new Set(g.goals.map(([match, half, minute, second]) => clipId({ match, half, minute, second }))),
          ),
      );
    goalCache
      .get(k)!
      .then((g) => live && setGoals(g))
      .catch(() => {
        goalCache.delete(k);
        if (live) setGoals(null);
      });
    return () => {
      live = false;
    };
  }, [key, kind, events]);
  return goals;
}

export const toRef = (r: ClipRow, window = false): ClipRef => ({
  match: r.match,
  half: r.half,
  minute: r.minute,
  second: r.second,
  window,
  title: r.family,
  detail: `${r.family} · vs ${r.opponent}, ${r.date}, half ${r.half} ${clock(r.minute, r.second)}${r.ended_in_shot ? " · ended in a shot" : ""}`,
});

/* Most recent first; possessions that ended in a shot lead when asked. */
export const pickRecent = (rows: ClipRow[], n: number, shotsFirst = false) =>
  [...rows]
    .sort(
      (a, b) =>
        (shotsFirst ? b.ended_in_shot - a.ended_in_shot : 0) || b.date.localeCompare(a.date) || b.minute - a.minute,
    )
    .slice(0, n);
