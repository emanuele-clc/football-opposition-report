import { useEffect, useState, type CSSProperties } from "react";
import { api, type GamePlan as Plan, type GPEvents, type TeamData, type TeamSummary } from "../api";
import { evidenceHref, Explain, GRADE_SAYS, GradeKey, GradeMark, Icon } from "../charts";
import { Note, Pitch, Replay, plain } from "../charts";
import { fmt, ordinal } from "../format";

const TAB_LABEL: Record<string, string> = {
  restarts: "Restarts",
  defending: "Defending",
  transitions: "Transitions",
  "build-up": "Families",
  setpieces: "Set pieces",
  matchups: "Matchups",
};
const MINE_KEY = "oppreport.mine";
type Topic = "priorities" | "with_ball" | "without_ball" | "transitions" | "set_pieces";
const QUESTIONS: [Topic, (t: string) => string][] = [
  ["priorities", () => "What matters most?"],
  ["with_ball", (t) => `How do we play out against ${t}?`],
  ["without_ball", (t) => `How do we defend against ${t}?`],
  ["transitions", () => "Where can we win the ball?"],
  ["set_pieces", () => "Set pieces?"],
];
const store = {
  get: () => {
    try {
      return localStorage.getItem(MINE_KEY) ?? "";
    } catch {
      return "";
    }
  },
  set: (v: string) => {
    try {
      localStorage.setItem(MINE_KEY, v);
    } catch {
      /* private mode */
    }
  },
};

const place = (r: number, of: number) =>
  r === 1 ? `highest of ${of}` : r === of ? `lowest of ${of}` : `${ordinal(r)} highest of ${of}`;
const unit = (u: string) => u as "pct" | "num" | "num2";

/* Goals (numbers) and xG per match (bars) by 15-minute slot: scored above the line, conceded below. */
function Timeline({ t }: { t: GPEvents["timeline"] }) {
  const max = Math.max(...t.flatMap((s) => [s.xg_for, s.xg_against]), 0.05);
  const H = 70,
    W = 60;
  return (
    <svg
      viewBox={`0 0 ${t.length * W + 20} ${2 * H + 40}`}
      className="timeline"
      role="img"
      aria-label={t.map((s) => `${s.slot}: ${s.goals_for} scored, ${s.goals_against} conceded`).join("; ")}
    >
      <line x1="10" x2={t.length * W + 10} y1={H + 20} y2={H + 20} stroke="currentColor" strokeOpacity="0.35" />
      <line
        x1={10 + 3 * W}
        x2={10 + 3 * W}
        y1="8"
        y2={2 * H + 32}
        stroke="currentColor"
        strokeOpacity="0.25"
        strokeDasharray="3 3"
      />
      {t.map((s, i) => {
        const x = 10 + i * W + 10,
          w = W - 20,
          hf = (H * s.xg_for) / max,
          ha = (H * s.xg_against) / max;
        return (
          <g key={s.slot} className="enter" style={{ "--i": i } as CSSProperties}>
            <rect x={x} y={H + 20 - hf} width={w} height={hf} rx="4" fill="var(--lime)" />
            <rect x={x} y={H + 20} width={w} height={ha} rx="4" fill="var(--coral)" />
            <text x={x + w / 2} y={H + 14 - hf} textAnchor="middle" fontSize="13" fontWeight="850" fill="currentColor">
              {s.goals_for}
            </text>
            <text x={x + w / 2} y={H + 36 + ha} textAnchor="middle" fontSize="13" fontWeight="850" fill="currentColor">
              {s.goals_against}
            </text>
            <text
              x={x + w / 2}
              y={2 * H + 38}
              textAnchor="middle"
              fontSize="10.5"
              fill="currentColor"
              fillOpacity="0.7"
            >
              {s.slot}'
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* Their own half (own goal on the left) in 3 x 3 zones: completion under pressure, against the other teams in the folder. */
function PressureZones({ pz, team }: { pz: NonNullable<Plan["pressure_zones"]>; team: string }) {
  return (
    <Pitch label={`${team}: pass completion under pressure by zone of their own half`}>
      {pz.zones.map((z, i) => {
        const d = z.diff ?? 0;
        const col = z.few ? "var(--board-raised)" : d < 0 ? "var(--coral)" : "var(--lime)";
        const a = z.few ? 0.35 : Math.min(0.9, 0.18 + Math.abs(d) * 5);
        const cx = (z.x0 + z.x1) / 2,
          cy = (z.y0 + z.y1) / 2;
        return (
          <g key={i} className="enter" style={{ "--i": i } as CSSProperties}>
            <rect
              x={z.x0 + 0.6}
              y={z.y0 + 0.6}
              width={z.x1 - z.x0 - 1.2}
              height={z.y1 - z.y0 - 1.2}
              rx="1.5"
              fill="var(--sticker)"
            />
            <rect
              x={z.x0 + 0.6}
              y={z.y0 + 0.6}
              width={z.x1 - z.x0 - 1.2}
              height={z.y1 - z.y0 - 1.2}
              rx="1.5"
              fill={col}
              fillOpacity={a}
              stroke={z.weaker ? "var(--sticker-ink)" : "none"}
              strokeWidth="0.9"
              strokeDasharray={z.weaker ? "2 1" : undefined}
            />
            <text
              x={cx}
              y={cy - 1.6}
              textAnchor="middle"
              fontSize="4.4"
              fontWeight="900"
              fontStyle="italic"
              fill="var(--sticker-ink)"
            >
              {Math.round(100 * z.up_completion)}%
            </text>
            <text x={cx} y={cy + 3} textAnchor="middle" fontSize="2.3" fontWeight="700" fill="var(--sticker-ink)">
              others {z.ref_completion != null ? Math.round(100 * z.ref_completion) : "–"}%
            </text>
            <text x={cx} y={cy + 6.4} textAnchor="middle" fontSize="2" fill="var(--sticker-ink)" fillOpacity="0.75">
              {z.few
                ? `only ${z.under_pressure}`
                : `n ${z.under_pressure} · ${Math.round(100 * z.up_long_share)}% long`}
            </text>
          </g>
        );
      })}
      <text x="90" y="41" textAnchor="middle" fontSize="3.2" fontWeight="800" fill="var(--pitch-line)">
        ← their own half · they attack →
      </text>
    </Pitch>
  );
}

/* Starting formation drawn schematically: goalkeeper, then one line per digit (e.g. 3-4-2-1), mirrored for the opponent. */
export function Shape({ raw, side }: { raw: string; side: "left" | "right" }) {
  const lines = raw
    .split("")
    .map(Number)
    .filter((n) => n > 0);
  const X = (x: number) => (side === "left" ? x : 120 - x);
  const col = side === "left" ? "var(--sky)" : "var(--coral)";
  const dots: [number, number][] = [[4, 40]];
  lines.forEach((n, i) => {
    const x = lines.length > 1 ? 15 + (i * 38) / (lines.length - 1) : 30;
    for (let j = 0; j < n; j++) dots.push([x, (80 * (j + 1)) / (n + 1)]);
  });
  return (
    <g>
      {dots.map(([x, y], i) => (
        <g key={i} className="enter" style={{ "--i": i } as CSSProperties}>
          <circle cx={X(x)} cy={y} r="2.6" fill={col} stroke="var(--sticker-ink)" strokeWidth="0.5" />
          {i === 0 && (
            <text x={X(x)} y={y + 1} textAnchor="middle" fontSize="2.6" fontWeight="850" fill="var(--sticker-ink)">
              GK
            </text>
          )}
        </g>
      ))}
    </g>
  );
}

export default function GamePlan({ d, teams, events }: { d: TeamData; teams: TeamSummary[]; events: boolean }) {
  const [mine, setMine] = useState(() => new URLSearchParams(location.search).get("mine") ?? store.get());
  const [plan, setPlan] = useState<Plan | null>(null);
  const [err, setErr] = useState("");
  const [topic, setTopic] = useState<Topic>("priorities");
  const [evs, setEvs] = useState<GPEvents | null | "none">(null);
  const [brk, setBrk] = useState(0);
  useEffect(() => {
    setEvs(null);
    api
      .gameplanEvents(d.key)
      .then(setEvs)
      .catch(() => setEvs("none"));
  }, [d.key]);
  const my = mine && mine !== d.key && teams.some((t) => t.key === mine) ? mine : "";

  useEffect(() => {
    setPlan(null);
    setErr("");
    api
      .gameplan(d.key, my)
      .then(setPlan)
      .catch((e) => setErr(String(e.message ?? e)));
  }, [d.key, my]);

  if (err)
    return (
      <div className="state">
        <h2>No game plan</h2>
        <p>{err}</p>
      </div>
    );
  const P = plan;
  const fo = P?.formations.opponent;
  const fm = P?.formations.mine;
  return (
    <>
      <div className="section-head">
        <h2>Game plan</h2>
        <Explain>
          Preparing to play {d.team}: their shape, how they play and where to look. Hints come from fixed rules on how
          they rank among the {P?.teams_in_folder ?? "…"} teams in this folder. They say where to look on video, not
          what will work.
        </Explain>
      </div>
      <div className="filters" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <a className="btn" href={`#/${d.key}/coach`} style={{ order: 2, marginLeft: "auto" }}>
          {Icon.print}
          <span>Coach sheet · one A4 page</span>
        </a>
        <button
          type="button"
          className="icon-btn"
          onClick={() => {
            document.querySelectorAll<HTMLDetailsElement>("details.gp-more").forEach((x) => (x.open = true));
            setTimeout(() => window.print(), 50);
          }}
          aria-label="Print the whole game plan, details included"
          style={{ order: 3 }}
        >
          {Icon.print}
          <span>Print all</span>
        </button>
        <label htmlFor="mine" style={{ fontWeight: 750 }}>
          Your team
        </label>
        <select
          id="mine"
          className="pill-select"
          value={my}
          onChange={(e) => {
            setMine(e.target.value);
            store.set(e.target.value);
          }}
        >
          <option value="">None (opponent only)</option>
          {teams
            .filter((t) => t.key !== d.key)
            .map((t) => (
              <option key={t.key} value={t.key}>
                {t.team}
              </option>
            ))}
        </select>
      </div>
      {!P ? (
        <div className="state" style={{ marginTop: 24 }}>
          <p>Loading…</p>
        </div>
      ) : (
        <>
          <div className="layout-split" style={{ marginTop: 24 }}>
            <section className="sticker" style={plain} aria-labelledby="gp-shape">
              <div className="pitch-wrap">
                <Pitch
                  label={`Starting formations: ${fm ? `${P.mine} ${fm.most_used[0]?.formation} against ` : ""}${d.team} ${fo?.most_used[0]?.formation ?? "unknown"}`}
                >
                  {fm?.most_used[0] && <Shape raw={fm.most_used[0].raw} side="left" />}
                  {fo?.most_used[0] && <Shape raw={fo.most_used[0].raw} side="right" />}
                </Pitch>
              </div>
              <div className="replay-cap">
                <div>
                  <h2 id="gp-shape">
                    {fm
                      ? `${fm.most_used[0]?.formation} vs ${fo?.most_used[0]?.formation ?? "?"}`
                      : `${d.team}: ${fo?.most_used[0]?.formation ?? "formation unknown"}`}
                  </h2>
                  <p>
                    Most used starting formation
                    {fm ? (
                      <>
                        s:{" "}
                        <b className="team-key" style={{ "--dot": "var(--sky)" } as CSSProperties}>
                          {P.mine}
                        </b>{" "}
                        left,{" "}
                        <b className="team-key" style={{ "--dot": "var(--coral)" } as CSSProperties}>
                          {d.team}
                        </b>{" "}
                        right
                      </>
                    ) : (
                      <>
                        ,{" "}
                        <b className="team-key" style={{ "--dot": "var(--coral)" } as CSSProperties}>
                          {d.team}
                        </b>{" "}
                        attacking right to left
                      </>
                    )}
                    . Schematic: the formation on the team sheet, not positions in play.
                  </p>
                </div>
              </div>
            </section>
            <div className="stack">
              {fo && (
                <div className="sticker pad">
                  <h3>{d.team}: formations</h3>
                  <table style={{ marginTop: 6 }}>
                    <thead>
                      <tr>
                        <th>Formation</th>
                        <th>Matches</th>
                        <th>Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fo.most_used.map((f) => (
                        <tr key={f.raw}>
                          <td>
                            <b>{f.formation}</b>
                          </td>
                          <td>{f.matches}</td>
                          <td>{fmt(f.matches / fo.matches, "pct")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>
                    Last 5:{" "}
                    {fo.last5.map((f, i) => (
                      <span
                        key={i}
                        className="chip"
                        style={{ ...plain, marginRight: 4 }}
                        title={`${f.date} vs ${f.opponent}`}
                      >
                        {f.formation}
                      </span>
                    ))}
                  </p>
                </div>
              )}
              <div className="sticker pad">
                <h3>How they play</h3>
                <ul className="read" style={{ marginTop: 6 }}>
                  {P.profile.map((r) => (
                    <li key={r.id}>
                      <GradeMark g={r.grade} href={evidenceHref(d.key)} none />
                      <b>{r.label}</b>: {fmt(r.value, unit(r.unit))}{" "}
                      <span className="s-muted">
                        ({r.provisional ? "not ranked: few matches" : place(r.rank, r.of)})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <section className="section" aria-labelledby="ai-h">
            <div className="section-head">
              <h2 id="ai-h">Coach brief</h2>
              <Explain>{P.brief.intro}</Explain>
            </div>
            <div className="sticker pad">
              <div className="pills" role="group" aria-label="Choose a question">
                {QUESTIONS.map(([t, label]) => (
                  <button key={t} type="button" aria-pressed={topic === t} onClick={() => setTopic(t)}>
                    {label(d.team)}
                  </button>
                ))}
              </div>
              <div className="brief enter" key={topic} aria-live="polite">
                <h3>{topic === "priorities" ? "Priorities" : P.brief.phases[topic].title}</h3>
                <ol>
                  {(topic === "priorities"
                    ? P.brief.priorities.length
                      ? P.brief.priorities
                      : [
                          `No rule fired: nothing in ${d.team}'s numbers is at the extremes. Prepare as usual and use the video.`,
                        ]
                    : P.brief.phases[topic].lines
                  ).map((l, i) => (
                    <li key={i}>
                      {topic === "priorities" && P.brief.priorities.length > 0 && (
                        <GradeMark g={P.brief.priority_grades?.[i]} href={evidenceHref(d.key)} none />
                      )}
                      {l}
                    </li>
                  ))}
                </ol>
                {topic === "priorities" && <GradeKey />}
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <Note kind="caution" tag="Hints, not advice">
                The rules were fixed in advance and are simple (top or bottom among the teams here). None was tested for
                whether following it wins matches: data like these cannot say which formation or style will work. Use
                them to choose what to watch, and decide with the staff.
              </Note>
            </div>
          </section>

          <section className="section" aria-labelledby="gp-h">
            <div className="section-head">
              <h2 id="gp-h">Where to look</h2>
              <Explain>
                {P.hints.length} hints fired. Each one shows the numbers that triggered it, with their evidence grade
                (A reliable to D not reliable; the hint takes the weakest grade of its opponent numbers). "Highest" or
                "lowest" is among the teams in this folder, which can be from other leagues and seasons.
              </Explain>
            </div>
            {P.hints.length === 0 ? (
              <p>No rule fired: {d.team} is not at the extremes of any measure here.</p>
            ) : (
              <div className="fam-row" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
                {P.hints.map((h, n) => (
                  <article
                    key={h.id}
                    className="sticker fam-front enter"
                    style={{ ...plain, "--i": n } as CSSProperties}
                  >
                    <div className="ribbon" />
                    <div className="body">
                      {h.side === "both" && (
                        <span className="chip" style={{ ...plain, marginBottom: 6 }}>
                          you vs them
                        </span>
                      )}
                      <h3 style={{ margin: "2px 0 6px" }}>
                        <GradeMark g={h.grade} href={evidenceHref(d.key)} none />
                        {h.title}
                      </h3>
                      <p>{h.why}</p>
                      {h.grade === "D" && <p className="grade-warn">{`Grade D: ${GRADE_SAYS.D}`}</p>}
                      <p style={{ color: "var(--sticker-ink)", fontWeight: 650 }}>{h.look}</p>
                      <p className="gp-ev">
                        {h.evidence.map((e, i) => (
                          <span key={i}>
                            <GradeMark g={e.grade} none />
                            {e.team && <b>{e.team === "you" ? P.mine : d.team}: </b>}
                            {e.label} {fmt(e.value, unit(e.unit))} · {place(e.rank, e.of)}
                            {e.id === "ppda" ? " (lower = more intense pressing)" : ""}
                          </span>
                        ))}
                      </p>
                      <a href={`#/${d.key}/${h.tab}`} style={{ fontWeight: 750, fontSize: 13 }}>
                        Check in {TAB_LABEL[h.tab] ?? h.tab} →
                      </a>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          {evs && evs !== "none" && (
            <section className="section" aria-labelledby="kp-h">
              <div className="section-head">
                <h2 id="kp-h">Key players</h2>
                <Explain>
                  From all {evs.matches} matches: top 3 per role. Per match = matches in which the player appears. Names
                  and shirt numbers as in the StatsBomb data.
                </Explain>
              </div>
              <div className="fam-row" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
                {evs.players.map((r, n) => (
                  <article
                    key={r.id}
                    className="sticker fam-front enter"
                    style={{ ...plain, "--i": n } as CSSProperties}
                  >
                    <div className="ribbon" />
                    <div className="body">
                      <h3 style={{ margin: "2px 0 8px" }}>{r.role}</h3>
                      <ol className="players">
                        {r.top.map((p, i) => (
                          <li key={p.full} title={p.full}>
                            <span className="shirt" data-first={i === 0 || undefined}>
                              {p.shirt ?? "–"}
                            </span>
                            <span className="pname">
                              {p.player}
                              {p.keeper && <small> GK</small>}
                            </span>
                            <span className="pval">
                              <b>{r.id === "xg" ? p.per_match.toFixed(2) : p.per_match.toFixed(1)}</b>
                              <small>
                                /match · {r.id === "xg" ? p.total.toFixed(1) : p.total} in {p.matches}
                              </small>
                            </span>
                          </li>
                        ))}
                      </ol>
                      <p style={{ fontSize: 12, marginTop: 8 }}>
                        {r.unit}. {r.note}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {P.watch_first && (
            <section className="section" aria-labelledby="wf-h">
              <div className="section-head">
                <h2 id="wf-h">Watch first</h2>
              </div>
              <div className="sticker pad watch-card">
                <p className="s-muted" style={{ fontSize: 12.5, margin: "4px 0 8px" }}>
                  {P.mine ? (
                    <>
                      Their matches against {P.watch_first.rule}: the closest to how {P.mine} defends.
                    </>
                  ) : (
                    <>
                      Pick your team above to see their matches against opponents that defended like you. Now:{" "}
                      {P.watch_first.rule}.
                    </>
                  )}
                </p>
                <ol className="watch">
                  {P.watch_first.matches.map((m) => (
                    <li key={m.match}>
                      <span>
                        <b>{m.opponent}</b>{" "}
                        <small>
                          {m.date} · {m.venue} · {m.opp_formation ? m.opp_formation.split("").join("-") : "–"} · opp.
                          PPDA {m.opp_ppda.toFixed(1)}
                        </small>
                      </span>
                      <span className="score">{m.score}</span>
                      <a
                        href={`#/${d.key}/clips/sequences?opponent=${encodeURIComponent(m.opponent)}`}
                        aria-label={`Clips against ${m.opponent}, ${m.date}`}
                      >
                        Clips →
                      </a>
                    </li>
                  ))}
                </ol>
              </div>
            </section>
          )}

          <details className="more gp-more">
            <summary>More detail: where pressing hurts them, breaks, fouls, when they score, past matches</summary>
            <div>
              {P.pressure_zones && (
                <section className="section" aria-labelledby="pz-h">
                  <div className="section-head">
                    <h2 id="pz-h">Where pressing hurts them</h2>
                    <Explain>
                      Their own half, own goal on the left. Each zone: share of their open-play passes completed when
                      under pressure, against the other {P.pressure_zones.teams_in_reference} teams in the same zone.
                      Red = below the others, green = above; dashed outline = at least 5 points below with 40+ passes.
                    </Explain>
                  </div>
                  <div className="layout-split">
                    <div className="sticker" style={plain}>
                      <div className="pitch-wrap">
                        <PressureZones pz={P.pressure_zones} team={d.team} />
                      </div>
                    </div>
                    <div className="stack">
                      <div className="sticker pad">
                        <h3>Overall</h3>
                        <p style={{ marginTop: 6 }}>
                          In their own half {d.team} complete{" "}
                          <b>{Math.round(100 * P.pressure_zones.total.completion)}%</b> of passes under pressure and{" "}
                          <b>{Math.round(100 * P.pressure_zones.total.free_completion)}%</b> when free (
                          {P.pressure_zones.total.passes} passes under pressure in {P.pressure_zones.matches} matches).
                        </p>
                        <p style={{ marginTop: 8 }}>
                          {P.pressure_zones.zones.some((z) => z.weaker) ? (
                            P.pressure_zones.zones.filter((z) => z.weaker).length >= 5 ? (
                              <>
                                Below the other teams in{" "}
                                <b>{P.pressure_zones.zones.filter((z) => z.weaker).length} of 9</b> zones: they are less
                                secure under pressure in general (often a more direct style), not weak in one place. The
                                darkest red zone is where the gap is largest.
                              </>
                            ) : (
                              <>
                                Zones clearly below the other teams:{" "}
                                <b>{P.pressure_zones.zones.filter((z) => z.weaker).length}</b>. Start the pressing plan
                                from the darkest red one and check it on video.
                              </>
                            )
                          ) : (
                            <>
                              No zone is clearly below the other teams: under pressure they play out about as well as
                              the others or better. Pressing them is not suggested by these numbers.
                            </>
                          )}
                        </p>
                      </div>
                      <Note kind="caution" tag="Read with care">
                        Pressure is StatsBomb's flag on the pass (a player pressing within a short time). Zones near
                        their own goal are hard for every team, which is why each zone is compared with the others in
                        the same place. Completion does not say whether the ball was then won.
                      </Note>
                    </div>
                  </div>
                </section>
              )}

              {P.breaks && (
                <section className="section" aria-labelledby="br-h">
                  <div className="section-head">
                    <h2 id="br-h">Where they hurt you on the break</h2>
                    <Explain>
                      Where {d.team} win the ball back (they attack left to right). Zone colour = share of their
                      recoveries there followed by a shot within 10 s; dots = each of the {P.breaks.shots.length}{" "}
                      recoveries that led to a shot, click one to replay it. Overall{" "}
                      {Math.round(1000 * P.breaks.rate) / 10}% of {P.breaks.n} recoveries.
                    </Explain>
                  </div>
                  <div className="layout-split">
                    <div className="sticker" style={plain}>
                      <div className="pitch-wrap">
                        <Pitch label={`${d.team}: recoveries followed by a shot within 10 seconds`}>
                          {P.breaks.zones.map((z, i) => {
                            const r = z.n ? z.shot10 / z.n : 0;
                            const few = z.n < 30;
                            return (
                              <g key={i}>
                                <rect
                                  x={z.x0 + 0.5}
                                  y={z.y0 + 0.5}
                                  width={z.x1 - z.x0 - 1}
                                  height={z.y1 - z.y0 - 1}
                                  rx="1.5"
                                  fill="var(--yellow)"
                                  fillOpacity={few ? 0.05 : Math.min(0.75, r * 8)}
                                />
                              </g>
                            );
                          })}
                          {P.breaks.shots.map((s, i) => (
                            <circle
                              key={i}
                              cx={s.x}
                              cy={s.y}
                              r={i === brk ? 1.6 : 1}
                              fill={i === brk ? "var(--yellow)" : "var(--coral)"}
                              stroke="var(--sticker-ink)"
                              strokeWidth="0.3"
                              style={{ cursor: "pointer" }}
                              onClick={() => setBrk(i)}
                            >
                              <title>{`${s.date} vs ${s.opponent}, ${s.minute}'`}</title>
                            </circle>
                          ))}
                          {P.breaks.zones.map((z, i) => {
                            const r = z.n ? z.shot10 / z.n : 0;
                            const t = z.n < 30 ? `n ${z.n}` : `${Math.round(100 * r)}% · n ${z.n}`;
                            return (
                              <g key={`l${i}`} pointerEvents="none">
                                <rect
                                  x={z.x0 + 1.2}
                                  y={z.y0 + 1.2}
                                  width={t.length * 1.45 + 2}
                                  height="4.2"
                                  rx="1"
                                  fill="var(--sticker-ink)"
                                  fillOpacity="0.8"
                                />
                                <text
                                  x={z.x0 + 2.2}
                                  y={z.y0 + 4.3}
                                  fontSize="2.6"
                                  fontWeight="800"
                                  fill="var(--sticker)"
                                >
                                  {t}
                                </text>
                              </g>
                            );
                          })}
                        </Pitch>
                      </div>
                    </div>
                    <div className="stack">
                      {events && P.breaks.shots.length > 0 ? (
                        <div className="sticker" style={plain}>
                          <Replay
                            teamKey={d.key}
                            index={Math.min(brk, P.breaks.shots.length - 1)}
                            onIndex={setBrk}
                            clips={P.breaks.shots.map((s) => ({
                              match: s.match,
                              half: s.half,
                              minute: s.minute,
                              second: s.second,
                              window: true,
                              title: `Recovery vs ${s.opponent} ${s.minute}'`,
                              detail: s.date,
                            }))}
                          />
                        </div>
                      ) : (
                        <Note kind="info" tag="Replays">
                          Replays need the raw events (ev/ in the data folder); the map works without them.
                        </Note>
                      )}
                      <Note kind="caution" tag="Read with care">
                        Same definitions as the Transitions sheet: a recovery is a change of control in open play; shot
                        within 10 s before the opponent touches the ball again. Darker zones are where losing the ball
                        to them cost most often.
                      </Note>
                    </div>
                  </div>
                </section>
              )}

              {P.foul_zones && (
                <section className="section" aria-labelledby="fz-h">
                  <div className="section-head">
                    <h2 id="fz-h">Where they foul</h2>
                    <Explain>
                      Fouls committed per match in each zone of their own half (own goal on the left), against the other{" "}
                      {P.foul_zones.teams_in_reference} teams; handballs excluded. Overall{" "}
                      {P.foul_zones.total_per_match.toFixed(1)} per match in their half, others{" "}
                      {P.foul_zones.ref_total_per_match?.toFixed(1) ?? "–"}.
                    </Explain>
                  </div>
                  <div className="layout-split">
                    <div className="sticker" style={plain}>
                      <div className="pitch-wrap">
                        <Pitch label={`${d.team}: fouls per match by zone of their own half`}>
                          {P.foul_zones.zones.map((z, i) => {
                            const diff = z.per_match - (z.ref_per_match ?? z.per_match);
                            const cx = (z.x0 + z.x1) / 2,
                              cy = (z.y0 + z.y1) / 2;
                            return (
                              <g key={i}>
                                <rect
                                  x={z.x0 + 0.6}
                                  y={z.y0 + 0.6}
                                  width={z.x1 - z.x0 - 1.2}
                                  height={z.y1 - z.y0 - 1.2}
                                  rx="1.5"
                                  fill="var(--sticker)"
                                />
                                <rect
                                  x={z.x0 + 0.6}
                                  y={z.y0 + 0.6}
                                  width={z.x1 - z.x0 - 1.2}
                                  height={z.y1 - z.y0 - 1.2}
                                  rx="1.5"
                                  fill={diff > 0 ? "var(--coral)" : "var(--lime)"}
                                  fillOpacity={Math.min(0.85, 0.15 + Math.abs(diff) * 2)}
                                />
                                <text
                                  x={cx}
                                  y={cy - 1}
                                  textAnchor="middle"
                                  fontSize="4.2"
                                  fontWeight="900"
                                  fontStyle="italic"
                                  fill="var(--sticker-ink)"
                                >
                                  {z.per_match.toFixed(2)}
                                </text>
                                <text
                                  x={cx}
                                  y={cy + 3.4}
                                  textAnchor="middle"
                                  fontSize="2.2"
                                  fontWeight="700"
                                  fill="var(--sticker-ink)"
                                >
                                  others {z.ref_per_match?.toFixed(2) ?? "–"}
                                </text>
                                <text
                                  x={cx}
                                  y={cy + 6.6}
                                  textAnchor="middle"
                                  fontSize="2"
                                  fill="var(--sticker-ink)"
                                  fillOpacity="0.75"
                                >
                                  {z.fouls} fouls · {z.cards} cards
                                </text>
                              </g>
                            );
                          })}
                          <text
                            x="90"
                            y="41"
                            textAnchor="middle"
                            fontSize="3.2"
                            fontWeight="800"
                            fill="var(--pitch-line)"
                          >
                            ← their own half · they attack →
                          </text>
                        </Pitch>
                      </div>
                    </div>
                    <Note kind="caution" tag="Read with care">
                      More fouls in a zone can mean they are often late there, or simply that the ball is there more
                      often against them. It is a place to check on video, not proof of a weakness.
                    </Note>
                  </div>
                </section>
              )}

              <div
                className="layout-2"
                style={{
                  marginTop: 28,
                  display: "grid",
                  gap: 24,
                  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                }}
              >
                {evs && evs !== "none" && (
                  <div className="sticker pad">
                    <h3>When they score and concede</h3>
                    <Timeline t={evs.timeline} />
                    <p className="s-muted" style={{ fontSize: 12.5 }}>
                      Bars: xG per match in each 15 minutes, <b style={{ color: "var(--sticker-ink)" }}>created</b>{" "}
                      above (green), <b style={{ color: "var(--sticker-ink)" }}>conceded</b> below (red). Numbers: goals
                      in the season. Stoppage time counts in the last slot of each half. Goals per slot are few: a
                      single slot can move a lot by chance.
                    </p>
                  </div>
                )}
                <div className="sticker pad">
                  <h3 id="past-h">What happened in their past matches</h3>
                  {P.opp_past.length ? (
                    <ul className="read" style={{ marginTop: 6 }}>
                      {P.opp_past.map((p, i) => (
                        <li key={i}>
                          <b>{p.label}</b> {p.ga} ({p.n_a} matches): {fmt(p.a, unit(p.unit))} vs{" "}
                          {fmt(p.b, unit(p.unit))} {p.gb} ({p.n_b}).
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ marginTop: 8 }}>
                      No clear difference between groups of their matches (pressing, back line, home/away).
                    </p>
                  )}
                  <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>
                    Only clear differences not linked to how the groups are formed; about one in 20 is expected by
                    chance. Details in <a href={`#/${d.key}/matchups`}>Matchups</a>.
                  </p>
                </div>
                {P.my_vs_press && (
                  <div className="sticker pad">
                    <h3>{P.mine} against a high press</h3>
                    <table style={{ marginTop: 6 }}>
                      <thead>
                        <tr>
                          <th>Per match</th>
                          <th>
                            {P.my_vs_press.groups[0]} ({P.my_vs_press.n_a})
                          </th>
                          <th>
                            {P.my_vs_press.groups[1]} ({P.my_vs_press.n_b})
                          </th>
                          <th>Verdict</th>
                        </tr>
                      </thead>
                      <tbody>
                        {P.my_vs_press.metrics.map((m) => (
                          <tr key={m.id}>
                            <td>{m.label}</td>
                            <td>{fmt(m.a, unit(m.unit))}</td>
                            <td>{fmt(m.b, unit(m.unit))}</td>
                            <td>
                              {m.verdict}
                              {m.linked ? "*" : ""}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="s-muted" style={{ fontSize: 12.5, marginTop: 10 }}>
                      From your own past matches. * partly by construction (shares events with the opponent PPDA that
                      forms the groups).
                    </p>
                  </div>
                )}
              </div>
            </div>
          </details>
        </>
      )}
    </>
  );
}
