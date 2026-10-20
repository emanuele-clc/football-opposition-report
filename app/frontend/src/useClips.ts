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
