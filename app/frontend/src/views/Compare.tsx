import { useEffect, useState, type CSSProperties } from "react";
import { api, type Rank, type TeamData, type TeamSummary } from "../api";
import { Explain, FamilyLanes, Note, Replay, ShareStrip } from "../charts";
import { fmt, ordinal } from "../format";
import { famLine, familyClips } from "./Overview";
import StyleMap from "./StyleMap";

/* Two teams on the same scales: every fact as a row of dots, the two teams highlighted. */
function DuoRow({ a, b, ka, kb }: { a: Rank; b: Rank; ka: string; kb: string }) {
  const vals = a.teams.map((t) => t.value),
    lo = Math.min(...vals),
    hi = Math.max(...vals);
  const pos = (v: number) => (hi === lo ? 50 : 4 + ((v - lo) / (hi - lo)) * 92);
  return (
    <div className="duo-row">
      <span className="val a">
        {fmt(a.value, a.unit)}
        <small>{ordinal(a.rank)}</small>
      </span>
      <div className="duo-mid">
        <span className="lab">
          {a.label}
          {a.caution && (
            <span className="flagged" title={a.caution}>
              {" "}
              *
            </span>
          )}
        </span>
        <div className="track" aria-hidden="true">
          {a.teams.map((t) => (
            <span
              key={t.key}
              className={`d${t.key === ka ? " us" : t.key === kb ? " them-dot" : ""}`}
              style={{ left: `${pos(t.value)}%` }}
            />
          ))}
        </div>
      </div>
      <span className="val b">
        {fmt(b.value, b.unit)}
        <small>{ordinal(b.rank)}</small>
      </span>
    </div>
  );
}

function Side({ d, events, tone }: { d: TeamData; events: boolean; tone: string }) {
  const P = d.report.phases["build-up"];
  const [pick, setPick] = useState(P.families[0].fam);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    setPick(P.families[0].fam);
    setIdx(0);
  }, [d.key]);
  const fam = P.families.find((f) => f.fam === pick) ?? P.families[0];
  return (
    <section className="sticker" style={{ "--rib": tone } as CSSProperties}>
      <span className="no">{d.team}</span>
      <div style={{ padding: "8px 2px 12px" }}>
        <ShareStrip
          families={P.families}
          pick={fam.fam}
          onPick={(f) => {
            setPick(f);
            setIdx(0);
          }}
        />
      </div>
      <Replay
        teamKey={d.key}
        clips={events ? familyClips(fam) : []}
        index={idx}
        onIndex={setIdx}
        fallback={<FamilyLanes families={P.families} pick={fam.fam} onPick={setPick} />}
      />
      <div className="replay-cap">
        <div>
          <h2>
            {fam.fam} of {d.team}
          </h2>
          <p>{famLine(fam)}</p>
        </div>
      </div>
    </section>
  );
}

export default function Compare({ d, teams, events }: { d: TeamData; teams: TeamSummary[]; events: boolean }) {
  const others = teams.filter((t) => t.key !== d.key);
  const [other, setOther] = useState(others[0]?.key ?? "");
  const [o, setO] = useState<TeamData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!other) return;
    let live = true;
    setO(null);
    setErr(null);
    api
      .team(other)
      .then((x) => live && setO(x))
      .catch((e) => live && setErr(e.message));
    return () => {
      live = false;
    };
  }, [other]);
  if (!others.length)
    return (
      <div className="state">
        <h2>Nothing to compare with</h2>
        <p>Only one team is in this data folder.</p>
      </div>
    );
  const groups = [...new Set(d.ranks.map((r) => r.group))];

  return (
    <>
      <div className="section-head">
        <h2>Compare</h2>
        <label className="field" style={{ minWidth: 240 }}>
          Compare {d.team} with
          <select value={other} onChange={(e) => setOther(e.target.value)}>
            {others.map((t) => (
              <option key={t.key} value={t.key}>
                {t.team} · {t.period.slice(0, 4)}/{t.period.slice(16, 18)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <section style={{ marginBottom: 40 }}>
        <StyleMap current={d.key} other={other} />
      </section>
      {err && (
        <Note kind="caution" tag="Not loaded">
          {err}
        </Note>
      )}
      {!o && !err && (
        <div aria-busy="true">
          <div className="skeleton" style={{ height: 300 }} />
        </div>
      )}
      {o && (
        <>
          <div className="duo-head">
            <span className="chip" style={{ "--rib": "var(--yellow)" } as CSSProperties}>
              {d.team}
            </span>
            <span className="small">same scales, all {d.ranks[0]?.of ?? ""} teams as grey dots</span>
            <span className="chip" style={{ "--rib": "var(--sky)" } as CSSProperties}>
              {o.team}
            </span>
          </div>
          <div className="ranks" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>
            {groups.map((g) => (
              <div key={g}>
                <div className="group-h">{g}</div>
                {d.ranks
                  .filter((r) => r.group === g)
                  .map((r) => {
                    const b = o.ranks.find((x) => x.id === r.id);
                    return b ? <DuoRow key={r.id} a={r} b={b} ka={d.key} kb={o.key} /> : null;
                  })}
              </div>
            ))}
          </div>
          <div className="stack" style={{ marginTop: 16 }}>
            {[...new Set(d.ranks.filter((r) => r.caution).map((r) => r.caution!))].map((c) => (
              <Note key={c} kind="caution" tag="* Caution">
                {c}
              </Note>
            ))}
          </div>

          <section className="section">
            <div className="section-head">
              <h2>Build-up, side by side</h2>
              <Explain>
                Families are fitted separately for each team: {d.team}'s B1 and {o.team}'s B1 are different groups that
                only share a label. Compare what they look like, not the codes.
              </Explain>
            </div>
            <div className="layout-2">
              <Side d={d} events={events} tone="var(--yellow)" />
              <Side d={o} events={events} tone="var(--sky)" />
            </div>
          </section>
        </>
      )}
    </>
  );
}
