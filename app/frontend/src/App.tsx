import React, { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { api, type Info, type TeamData, type TeamSummary } from "./api";
import { Icon } from "./charts";
import Clips from "./views/Clips";
import Compare from "./views/Compare";
import Review from "./views/Review";
import Families from "./views/Families";
import NewTeam from "./views/NewTeam";
import Overview from "./views/Overview";
import Restarts from "./views/Restarts";
import SetPieces from "./views/SetPieces";
import Transitions from "./views/Transitions";

const TABS: [string, string][] = [
  ["overview", "Overview"], ["build-up", "Families"], ["restarts", "Restarts"],
  ["setpieces", "Set pieces"], ["transitions", "Transitions"], ["clips", "Clips"], ["compare", "Compare"], ["review", "Review"],
];
const TOUR = ["overview", "build-up", "restarts", "setpieces", "transitions", "compare"];
const TOUR_MS = 15000;

// Route: #/<team key>/<tab>[/<clip list>][?family=B1]
interface Route { key: string; tab: string; kind: string; family: string }
const parse = (): Route => {
  const [path, query] = decodeURIComponent(location.hash.replace(/^#\/?/, "")).split("?");
  const [key = "", tab = "overview", kind = "sequences"] = path.split("/");
  return { key, tab: tab === "prep" ? "overview" : tab, kind, family: new URLSearchParams(query ?? "").get("family") ?? "" };
};
const href = (r: Partial<Route> & { key: string }) =>
  `#/${encodeURIComponent(r.key)}/${r.tab ?? "overview"}${r.tab === "clips" ? `/${r.kind ?? "sequences"}` : ""}${r.family ? `?family=${encodeURIComponent(r.family)}` : ""}`;

const stored = (): "dark" | "light" => {
  const q = new URLSearchParams(location.search).get("theme");
  if (q === "light" || q === "dark") return q;
  try { return localStorage.getItem("theme") === "light" ? "light" : "dark"; } catch { return "dark"; }
};

export default function App() {
  const [route, setRoute] = useState<Route>(parse);
  const [info, setInfo] = useState<Info | null>(null);
  const [teams, setTeams] = useState<TeamSummary[] | null>(null);
  const [data, setData] = useState<TeamData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState(stored);
  const [tour, setTour] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch { /* private window */ }
  }, [theme]);

  const loadTeams = useCallback(() => api.teams().then(setTeams).catch((e) => setError(e.message)), []);
  useEffect(() => {
    const on = () => {
      const next = parse();
      const swap = () => flushSync(() => setRoute(next));
      const vt = (document as Document & { startViewTransition?: (cb: () => void) => void }).startViewTransition;
      if (vt && !matchMedia("(prefers-reduced-motion: reduce)").matches) vt.call(document, swap); else swap();
      window.scrollTo({ top: 0 });
    };
    addEventListener("hashchange", on);
    api.info().then(setInfo).catch(() => undefined);
    loadTeams();
    return () => removeEventListener("hashchange", on);
  }, [loadTeams]);

  useEffect(() => { if (teams?.length && !route.key) location.replace(href({ key: teams[0].key })); }, [teams, route.key]);

  useEffect(() => {
    if (!route.key || route.key === "new") return;
    setError(null);
    api.team(route.key).then(setData).catch((e) => { setData(null); setError(e.message); });
  }, [route.key]);

  const current = route.key === "new" ? null : data && data.key === route.key ? data : null;
  useEffect(() => {
    const t = TABS.find(([k]) => k === route.tab)?.[1] ?? "";
    document.title = current ? `${current.team} · ${t} · Opposition report` : "Opposition report";
  }, [current, route.tab]);

  // Presentation tour: walks through the sections, then to the next team. Esc or a click on the pill stops it.
  useEffect(() => {
    if (!tour) return;
    const stop = (e: KeyboardEvent) => { if (e.key === "Escape") setTour(false); };
    addEventListener("keydown", stop);
    const t = setTimeout(() => {
      const r = parse(), i = TOUR.indexOf(r.tab);
      if (i >= 0 && i < TOUR.length - 1) location.hash = href({ key: r.key, tab: TOUR[i + 1] });
      else if (teams?.length) { const k = teams.findIndex((x) => x.key === r.key); location.hash = href({ key: teams[(k + 1) % teams.length].key, tab: "overview" }); }
    }, TOUR_MS);
    return () => { clearTimeout(t); removeEventListener("keydown", stop); };
  }, [tour, route, teams]);

  const go = (tab: string, family = "") => {
    if (!current) return;
    const [t, kind] = tab.split(":");
    location.hash = href({ key: current.key, tab: t, kind: kind ?? "sequences", family });
  };
  const events = !!info?.has_events;

  return (
    <>
      <header className="bar">
        <a className="brand" href={current ? href({ key: current.key }) : "#/"}>Opposition report</a>
        <label className="sr" htmlFor="team">Team</label>
        <select id="team" className="pill-select" value={route.key === "new" ? "" : route.key}
          onChange={(e) => { location.hash = href({ key: e.target.value, tab: route.tab === "clips" || route.key === "new" ? "overview" : route.tab }); }}>
          {route.key === "new" && <option value="">Choose a team</option>}
          {teams?.map((t) => <option key={t.key} value={t.key}>{t.team} · {t.period.slice(0, 4)}/{t.period.slice(16, 18)}</option>)}
        </select>
        <nav className="sections" aria-label="Sections">
          {TABS.map(([k, label]) => (
            <a key={k} href={route.key && route.key !== "new" ? href({ key: route.key, tab: k }) : "#/"} aria-current={(route.tab === k || (k === "build-up" && route.tab === "advanced")) && route.key !== "new" ? "page" : undefined}>{label}</a>
          ))}
        </nav>
        <div className="bar-actions">
          {info?.can_generate && <a className="icon-btn" href="#/new" aria-current={route.key === "new" ? "page" : undefined} aria-label="Add a team">{Icon.plus}<span>Add team</span></a>}
          <button className="icon-btn" type="button" onClick={() => { if (!tour && route.key !== "new" && !TOUR.includes(route.tab)) location.hash = href({ key: route.key, tab: "overview" }); setTour(!tour); }} aria-pressed={tour} aria-label={tour ? "Stop the presentation tour" : "Start the presentation tour"}>{Icon.tour}<span>Tour</span></button>
          <button className="icon-btn" type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>{theme === "dark" ? Icon.sun : Icon.moon}</button>
          <button className="icon-btn" type="button" onClick={() => print()} aria-label="Print this page">{Icon.print}<span>Print</span></button>
        </div>
      </header>

      {route.key === "new" ? (
        <main><NewTeam info={info} known={teams?.map((t) => t.team) ?? []} done={(k) => { loadTeams(); location.hash = href({ key: k }); }} /></main>
      ) : error && !current ? (
        <div className="state">
          <h2>Could not load the report</h2>
          <p>{error}</p>
          <p className="small">The app reads the files written by <code>src/oppreport.py</code>. Check that the API is running (<code>python -X utf8 app\run.py</code>) and that the data folder holds report_&lt;Team&gt;.json.</p>
        </div>
      ) : teams && teams.length === 0 ? (
        <div className="state">
          <h2>No reports in this folder yet</h2>
          <p>The app is reading <b>{info?.data_dir}</b> and found no report_&lt;Team&gt;.json. {info?.can_generate ? <a href="#/new">Generate one for a team.</a> : "Run src/oppreport.py for a team, or start the app with --data-dir on a folder with reports."}</p>
        </div>
      ) : !current ? (
        <main aria-busy="true"><div className="skeleton" style={{ height: 60, width: "45%" }} /><div className="skeleton" style={{ height: 420 }} />{Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton" />)}</main>
      ) : (
        <>
          <div className="team-head">
            <h1>{current.team}</h1>
            <div className="facts">
              <span><b>{current.matches} matches</b>{current.period.replace(" to ", " – ")}</span>
              <span><b>{current.sequences.toLocaleString("en")} sequences</b>{current.report.phases["build-up"].n} build-up · {current.report.phases.advanced.n} advanced</span>
              <span><b>{current.references.length} other teams</b>to compare with</span>
            </div>
          </div>
          <main key={current.key}>
            {route.tab === "overview" && <Overview d={current} events={events} go={go} />}
            {(route.tab === "build-up" || route.tab === "advanced") && <Families key={route.tab} d={current} phase={route.tab} events={events} family={route.family} go={go} />}
            {route.tab === "restarts" && <Restarts d={current} events={events} go={go} />}
            {route.tab === "setpieces" && <SetPieces d={current} events={events} go={go} />}
            {route.tab === "transitions" && <Transitions d={current} events={events} go={go} />}
            {route.tab === "compare" && teams && <Compare d={current} teams={teams} events={events} />}
            {route.tab === "review" && <Review d={current} events={events} />}
            {route.tab === "clips" && (
              <Clips d={current} kind={current.clips.includes(route.kind) ? route.kind : "sequences"} family={route.family} events={events}
                setFilter={(kind, family) => { location.hash = href({ key: current.key, tab: "clips", kind, family }); }} />
            )}
          </main>
        </>
      )}
      {tour && (
        <button type="button" className="tour-pill no-print" onClick={() => setTour(false)} aria-label="Stop the presentation tour">
          Tour · {TABS.find(([k]) => k === route.tab)?.[1]} <span className="bar-t" key={route.key + route.tab}><i style={{ "--tour": `${TOUR_MS}ms` } as React.CSSProperties} /></span> Esc to stop
        </button>
      )}
      <footer>
        <span>Automated Football Opposition Report · master's thesis prototype. Descriptive only: no number here was tested as a hypothesis unless the thesis protocol says so.</span>
        <span>Data: StatsBomb Open Data (non-commercial licence){info ? ` · ${info.data_dir}` : ""}</span>
      </footer>
    </>
  );
}
