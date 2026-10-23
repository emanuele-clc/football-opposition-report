import { useEffect, useState } from "react";
import { api, type GamePlan as Plan, type GPEvents, type TeamData } from "../api";
import { GradeMark, Icon, Pitch } from "../charts";
import { fmt } from "../format";
import { Shape } from "./GamePlan";

/* One A4 page for the coach: built from the same numbers as Game plan, nothing new is estimated here. */
const place = (r: number, of: number) =>
  r === 1 ? `highest of ${of}` : r === of ? `lowest of ${of}` : `${r} of ${of}`;

export default function CoachSheet({ d }: { d: TeamData }) {
  const mine = (() => {
    try {
      return new URLSearchParams(location.search).get("mine") ?? localStorage.getItem("oppreport.mine") ?? "";
    } catch {
      return "";
    }
  })();
  const [P, setP] = useState<Plan | null>(null);
  const [E, setE] = useState<GPEvents | null>(null);
  useEffect(() => {
    api
      .gameplan(d.key, mine && mine !== d.key ? mine : "")
      .then(setP)
      .catch(() => setP(null));
    api
      .gameplanEvents(d.key)
      .then(setE)
      .catch(() => setE(null));
  }, [d.key, mine]);
  if (!P)
    return (
      <div className="state">
        <p>Loading…</p>
      </div>
    );
  const fo = P.formations.opponent?.most_used[0];
  const fm = P.formations.mine?.most_used[0];
  const role = (id: string) => E?.players.find((r) => r.id === id)?.top[0];
  const weak = P.pressure_zones?.zones.filter((z) => z.weaker).sort((a, b) => (a.diff ?? 0) - (b.diff ?? 0))[0];
  const slot = E ? [...E.timeline].sort((a, b) => b.goals_for - a.goals_for)[0] : null;
  const recentGoals =
    E?.goals
      ?.filter((g) => g.side === "for")
      .slice(-3)
      .reverse() ?? [];
  const gf = E?.goals?.filter((g) => g.side === "for").length,
    ga = E?.goals?.filter((g) => g.side === "against").length;

  return (
    <div className="coach">
      <div className="coach-actions no-print">
        <a href={`#/${d.key}/gameplan`}>← Game plan</a>
        <button type="button" className="icon-btn" onClick={() => window.print()}>
          {Icon.print}
          <span>Print (A4)</span>
        </button>
      </div>
      <header className="coach-head">
        <div>
          <small>Opponent</small>
          <h1>{d.team}</h1>
          <p>
            {d.matches} matches · {d.period}
            {P.mine ? ` · prepared for ${P.mine}` : ""}
          </p>
        </div>
        <div className="coach-shape">
          <Pitch label="Starting formations">
            {fm && <Shape raw={fm.raw} side="left" />}
            {fo && <Shape raw={fo.raw} side="right" />}
          </Pitch>
          <p>
            <b>{fo?.formation ?? "?"}</b> in{" "}
            {fo ? Math.round((100 * fo.matches) / (P.formations.opponent?.matches ?? 1)) : 0}% of matches
            {fm ? (
              <>
                {" "}
                · you: <b>{fm.formation}</b>
              </>
            ) : null}
          </p>
        </div>
      </header>

      <section className="coach-block">
        <h2>What matters</h2>
        <ol>
          {(P.brief.priorities.length
            ? P.brief.priorities
            : ["Nothing in their numbers is at the extremes: prepare as usual and use the video."]
          ).map((t, i) => (
            <li key={i}>
              <GradeMark g={P.brief.priority_grades?.[i]} />
              {t}
            </li>
          ))}
        </ol>
      </section>

      <div className="coach-grid">
        <section className="coach-block">
          <h2>How they play</h2>
          <ul>
            {P.profile.slice(0, 5).map((r) => (
              <li key={r.id}>
                <GradeMark g={r.grade} />
                {r.label}: <b>{fmt(r.value, r.unit as "num")}</b>{" "}
                <small>({r.provisional ? "not ranked: few matches" : place(r.rank, r.of)})</small>
              </li>
            ))}
          </ul>
        </section>
        <section className="coach-block">
          <h2>Key players</h2>
          <ul>
            {[
              ["buildup", "Build-up goes through"],
              ["xg", "Main threat"],
              ["corners", "Corners"],
              ["losses", "Loses the ball in own half"],
            ].map(([id, l]) => {
              const p = role(id);
              return p ? (
                <li key={id}>
                  {l}:{" "}
                  <b>
                    {p.shirt != null ? `#${p.shirt} ` : ""}
                    {p.player}
                  </b>
                  {p.keeper ? " (GK)" : ""}
                </li>
              ) : null;
            })}
          </ul>
        </section>
        <section className="coach-block">
          <h2>Pressing them</h2>
          <p>
            {weak ? (
              <>
                Weakest zone under pressure:{" "}
                <b>
                  {weak.y0 === 0 ? "left" : weak.y0 < 30 ? "centre" : "right"},{" "}
                  {weak.x0 === 0 ? "around their box" : weak.x0 === 20 ? "their own third" : "just inside their half"}
                </b>
                : {Math.round(100 * weak.up_completion)}% completed vs {Math.round(100 * (weak.ref_completion ?? 0))}%
                for other teams.
              </>
            ) : (
              <>No own-half zone where they are clearly worse than other teams under pressure.</>
            )}
          </p>
        </section>
        <section className="coach-block">
          <h2>Goals</h2>
          <p>
            {gf ?? "–"} scored, {ga ?? "–"} conceded.
            {slot ? (
              <>
                {" "}
                Most goals scored {slot.slot}' ({slot.goals_for}).
              </>
            ) : null}
          </p>
          {recentGoals.length > 0 && (
            <>
              <p>Their last {recentGoals.length} goals:</p>
              <ul>
                {recentGoals.map((g, i) => (
                  <li key={i}>
                    <small>
                      {g.date} vs {g.opponent} {g.minute}'
                    </small>{" "}
                    {g.scorer} · {g.origin}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      {P.watch_first && (
        <section className="coach-block">
          <h2>Watch first</h2>
          <ol>
            {P.watch_first.matches.slice(0, 3).map((m) => (
              <li key={m.match}>
                {m.date} vs <b>{m.opponent}</b> {m.score}{" "}
                <small>
                  ({m.opp_formation ? m.opp_formation.split("").join("-") : "–"}, opp. PPDA {m.opp_ppda.toFixed(1)})
                </small>
              </li>
            ))}
          </ol>
        </section>
      )}
      <p className="coach-foot">
        Descriptive, from StatsBomb open data. Hints say where to look on video, not what will win. Letters: evidence
        grade of the number (checked on 70 unseen teams), A reliable, B useful, C half reliable, D not reliable.
        Automated Football Opposition Report.
      </p>
    </div>
  );
}
