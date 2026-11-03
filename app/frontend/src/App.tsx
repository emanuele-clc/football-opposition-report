import React, { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { api, type Info, type Provider, type TeamData, type TeamSummary } from "./api";
import { PROVIDER, PROVIDER_NAME, switchProvider, type ProviderId } from "./provider";
import { Icon } from "./charts";
import Clips from "./views/Clips";
import Compare from "./views/Compare";
import Defending from "./views/Defending";
import Evidence from "./views/Evidence";
import GamePlan from "./views/GamePlan";
import CoachSheet from "./views/CoachSheet";
import Goals from "./views/Goals";
import Matchups from "./views/Matchups";
import Review from "./views/Review";
import Families from "./views/Families";
import NewTeam from "./views/NewTeam";
import Overview from "./views/Overview";
import Restarts from "./views/Restarts";
import SetPieces from "./views/SetPieces";
import Threat from "./views/Threat";
import Transitions from "./views/Transitions";
import TrackingLab from "./views/TrackingLab";
import { LANGS, setLanguage, storedLanguage, type Lang } from "./i18n";

const TABS: [string, string][] = [
  ["overview", "Overview"],
  ["gameplan", "Game plan"],
  ["coach", "Coach sheet"],
  ["evidence", "Evidence"],
  ["goals", "Goals"],
  ["build-up", "Families"],
  ["restarts", "Restarts"],
  ["setpieces", "Set pieces"],
  ["threat", "Threat"],
  ["transitions", "Transitions"],
  ["defending", "Defending"],
  ["matchups", "Matchups"],
  ["clips", "Clips"],
  ["compare", "Compare"],
  ["tracking", "Tracking lab"],
  ["review", "Review"],
];
/* The top bar names the group, the row under the team name the section.
   Two views of the same report. Analyst (default): only what an analyst opens to prepare the next match (summary,
   game plan, set pieces and restarts, without the ball, clips). Full: every section, including the thesis pages
   (evidence, families, threat, compare, matchups, review, tracking lab). Pages outside the analyst view still open
   from links (grades, key points, "every number per family"); they just have no menu entry there. */
const GROUPS_FULL: [string, string[]][] = [
  ["Summary", ["overview", "gameplan", "coach", "evidence"]],
  ["With the ball", ["build-up", "threat", "restarts", "setpieces", "goals"]],
  ["Without the ball", ["transitions", "defending"]],
  ["Clips", ["clips"]],
  ["More", ["compare", "matchups", "review", "tracking"]],
];
const GROUPS_ANALYST: [string, string[]][] = [
  ["Summary", ["overview"]],
  ["Game plan", ["gameplan"]],
  ["Set pieces", ["setpieces", "restarts"]],
  ["Without the ball", ["defending", "transitions"]],
  ["Clips", ["clips"]],
];
type View = "analyst" | "full";
/* "advanced" lives under the families tab and the coach sheet under the game plan. */
const MENU_TAB: Record<string, string> = { advanced: "build-up", coach: "gameplan" };
const groupOf = (tab: string, groups: [string, string[]][]) => groups.find(([, t]) => t.includes(MENU_TAB[tab] ?? tab));
const storedView = (): View => {
  const q = new URLSearchParams(location.search).get("view");
  if (q === "full" || q === "analyst") return q;
  try {
    return localStorage.getItem("view") === "full" ? "full" : "analyst";
  } catch {
    return "analyst";
  }
};
const TOUR = [
  "overview",
  "gameplan",
  "goals",
  "build-up",
  "threat",
  "restarts",
  "setpieces",
  "transitions",
  "defending",
  "compare",
  "evidence",
];
const TOUR_MS = 15000;

// Route: #/<team key>/<tab>[/<clip list>][?family=B1]
interface Route {
  key: string;
  tab: string;
  kind: string;
  family: string;
}
const parse = (): Route => {
  const [path, query] = decodeURIComponent(location.hash.replace(/^#\/?/, "")).split("?");
  const [key = "", tab = "overview", kind = "sequences"] = path.split("/");
  return {
    key,
    tab: tab === "prep" ? "overview" : tab,
    kind,
    family: new URLSearchParams(query ?? "").get("family") ?? "",
  };
};
const href = (r: Partial<Route> & { key: string }) =>
  `#/${encodeURIComponent(r.key)}/${r.tab ?? "overview"}${r.tab === "clips" ? `/${r.kind ?? "sequences"}` : ""}${r.family ? `?family=${encodeURIComponent(r.family)}` : ""}`;

const stored = (): "dark" | "light" => {
  const q = new URLSearchParams(location.search).get("theme");
  if (q === "light" || q === "dark") return q;
  try {
    return localStorage.getItem("theme") === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
};

export default function App() {
  const [route, setRoute] = useState<Route>(parse);
  const [info, setInfo] = useState<Info | null>(null);
  const [teams, setTeams] = useState<TeamSummary[] | null>(null);
  const [data, setData] = useState<TeamData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState(stored);
  const [tour, setTour] = useState(false);
  const [lang, setLang] = useState<Lang>(storedLanguage);
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [view, setView] = useState<View>(storedView);
  const full = view === "full";
  const GROUPS = full ? GROUPS_FULL : GROUPS_ANALYST;
  const group = groupOf(route.tab, GROUPS);
  const menu = useRef<HTMLDetailsElement>(null);
  const close = () => {
    if (menu.current) menu.current.open = false;
  };
  // The settings menu closes on Esc, on a click outside it, and when the page changes.
  useEffect(() => {
    const out = (e: PointerEvent) => {
      if (menu.current?.open && !menu.current.contains(e.target as Node)) menu.current.open = false;
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && menu.current?.open) {
        menu.current.open = false;
        menu.current.querySelector("summary")?.focus();
      }
    };
    addEventListener("pointerdown", out);
    addEventListener("keydown", esc);
    return () => {
      removeEventListener("pointerdown", out);
      removeEventListener("keydown", esc);
    };
  }, []);
  useEffect(close, [route.tab, route.key]);

  useEffect(() => {
    try {
      localStorage.setItem("view", view);
    } catch {
      /* private window */
    }
    if (view === "analyst") setTour(false);
  }, [view]);

  useEffect(() => {
    setLanguage(lang);
    try {
      localStorage.setItem("lang", lang);
    } catch {
      /* private window */
    }
  }, [lang]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("theme", theme);
    } catch {
      /* private window */
    }
  }, [theme]);

  const loadTeams = useCallback(
    () =>
      api
        .teams()
        .then(setTeams)
        .catch((e) => setError(e.message)),
    [],
  );
  useEffect(() => {
    const on = () => {
      const next = parse();
      const swap = () => flushSync(() => setRoute(next));
      const vt = (document as Document & { startViewTransition?: (cb: () => void) => void }).startViewTransition;
      if (vt && !matchMedia("(prefers-reduced-motion: reduce)").matches) vt.call(document, swap);
      else swap();
      window.scrollTo({ top: 0 });
    };
    addEventListener("hashchange", on);
    api
      .info()
      .then(setInfo)
      .catch(() => undefined);
    api
      .providers()
      .then(setProviders)
      .catch(() => undefined);
    loadTeams();
    return () => removeEventListener("hashchange", on);
  }, [loadTeams]);

  useEffect(() => {
    if (teams?.length && !route.key) location.replace(href({ key: teams[0].key }));
  }, [teams, route.key]);

  useEffect(() => {
    if (!route.key || route.key === "new") return;
    setError(null);
    api
      .team(route.key)
      .then(setData)
      .catch((e) => {
        setData(null);
        setError(e.message);
      });
  }, [route.key]);

  const current = route.key !== "new" && data && data.key === route.key ? data : null;
  useEffect(() => {
    const t = TABS.find(([k]) => k === (route.tab === "advanced" ? "build-up" : route.tab))?.[1] ?? "";
    document.title = current ? `${current.team} · ${t} · Opposition report` : "Opposition report";
  }, [current, route.tab]);

  // Presentation tour: walks through the sections, then to the next team. Esc or a click on the pill stops it.
  useEffect(() => {
    if (!tour) return;
    const stop = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTour(false);
    };
    addEventListener("keydown", stop);
    const t = setTimeout(() => {
      const r = parse(),
        i = TOUR.indexOf(r.tab);
      if (i >= 0 && i < TOUR.length - 1) location.hash = href({ key: r.key, tab: TOUR[i + 1] });
      else if (teams?.length) {
        const k = teams.findIndex((x) => x.key === r.key);
        location.hash = href({ key: teams[(k + 1) % teams.length].key, tab: "overview" });
      }
    }, TOUR_MS);
    return () => {
      clearTimeout(t);
      removeEventListener("keydown", stop);
    };
  }, [tour, route, teams]);

  const go = (tab: string, family = "") => {
    if (!current) return;
    const [t, kind] = tab.split(":");
    location.hash = href({ key: current.key, tab: t, kind: kind ?? "sequences", family });
  };
  const events = !!info?.has_events;
  const here = providers?.find((p) => p.id === PROVIDER);
  const season = (y: string) => `${y}/${String(Number(y) + 1).slice(2)}`;

  return (
    <>
      <header className="bar">
        <a className="brand" href={current ? href({ key: current.key }) : "#/"}>
          Opposition report
        </a>
        <label className="sr" htmlFor="team">
          Team
        </label>
        <select
          id="team"
          className="pill-select"
          value={route.key === "new" || !teams?.some((t) => t.key === route.key) ? "" : route.key}
          onChange={(e) => {
            location.hash = href({
              key: e.target.value,
              tab: route.tab === "clips" || route.key === "new" ? "overview" : route.tab,
            });
          }}
        >
          {(route.key === "new" || (teams && !teams.some((t) => t.key === route.key))) && (
            <option value="">Choose a team</option>
          )}
          {teams?.map((t) => (
            <option key={t.key} value={t.key}>
              {t.team} · {t.period.slice(0, 4)}/{t.period.slice(16, 18)}
              {t.provisional ? ` · ${t.matches} matches only` : ""}
            </option>
          ))}
        </select>
        <nav className="sections" aria-label="Sections">
          {GROUPS.map(([label, tabs]) => (
            <a
              key={label}
              href={route.key && route.key !== "new" ? href({ key: route.key, tab: tabs[0] }) : "#/"}
              aria-current={group?.[0] === label && route.key !== "new" ? "true" : undefined}
            >
              {label}
            </a>
          ))}
        </nav>
        {/* Everything that is set once and rarely changed lives behind one button, so the bar keeps only team and
            sections. The summary names the live data and language, so the state stays visible while closed. */}
        <details className="settings" ref={menu}>
          <summary className="icon-btn" aria-label="Settings: data, view, language, theme, print">
            {Icon.sliders}
            <span translate="no">
              {PROVIDER_NAME} · {lang.toUpperCase()}
            </span>
          </summary>
          <div className="settings-pop">
            {providers && providers.length > 1 && (
              <div className="set-row">
                <span className="set-label" id="set-data">
                  Data
                </span>
                <div className="edition" role="radiogroup" aria-labelledby="set-data">
                  {providers.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      role="radio"
                      aria-checked={p.id === PROVIDER}
                      onClick={() => switchProvider(p.id as ProviderId, route.key, route.tab)}
                      title={`${p.name} data: ${p.teams} teams, season ${p.seasons.map(season).join(", ")}. Values and ranks are never mixed between providers.`}
                    >
                      <span className="ed-name">{p.name}</span>
                      <span className="ed-season">
                        {p.seasons.length === 1 ? season(p.seasons[0]) : `${p.teams} teams`}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="set-row">
              <span className="set-label" id="set-view">
                View
              </span>
              <div className="edition" role="radiogroup" aria-labelledby="set-view">
                {(
                  [
                    ["analyst", "Analyst", "Only what you need to prepare the next match"],
                    ["full", "Full report", "Every section, including the thesis pages (evidence, families, compare, review)"],
                  ] as const
                ).map(([k, l, t]) => (
                  <button key={k} type="button" role="radio" aria-checked={view === k} onClick={() => setView(k)} title={t}>
                    <span className="ed-name">{l}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="set-row">
              <span className="set-label" id="set-lang">
                Language
              </span>
              <div className="edition" role="radiogroup" aria-labelledby="set-lang" translate="no">
                {LANGS.map(([k, name]) => (
                  <button key={k} type="button" role="radio" aria-checked={lang === k} onClick={() => setLang(k)}>
                    <span className="ed-name">{name}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="set-row">
              <span className="set-label" id="set-theme">
                Theme
              </span>
              <div className="edition" role="radiogroup" aria-labelledby="set-theme">
                {(
                  [
                    ["dark", "Dark"],
                    ["light", "Light"],
                  ] as const
                ).map(([k, l]) => (
                  <button key={k} type="button" role="radio" aria-checked={theme === k} onClick={() => setTheme(k)}>
                    <span className="ed-name">{l}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="set-actions">
              <button
                className="icon-btn"
                type="button"
                onClick={() => {
                  close();
                  setTimeout(() => print(), 50);
                }}
              >
                {Icon.print}
                <span>Print this page</span>
              </button>
              {full && info?.can_generate && (
                <a className="icon-btn" href="#/new" onClick={close}>
                  {Icon.plus}
                  <span>Add team</span>
                </a>
              )}
              {full && (
                <button
                  className="icon-btn"
                  type="button"
                  onClick={() => {
                    close();
                    if (!tour && route.key !== "new" && !TOUR.includes(route.tab))
                      location.hash = href({ key: route.key, tab: "overview" });
                    setTour(!tour);
                  }}
                  aria-pressed={tour}
                >
                  {Icon.tour}
                  <span>{tour ? "Stop tour" : "Presentation tour"}</span>
                </button>
              )}
            </div>
          </div>
        </details>
      </header>

      {route.key === "new" ? (
        <main>
          <NewTeam
            info={info}
            known={teams?.map((t) => t.team) ?? []}
            done={(k) => {
              loadTeams();
              location.hash = href({ key: k });
            }}
          />
        </main>
      ) : error && !current ? (
        <div className="state">
          <h2>Could not load the report</h2>
          <p>{error}</p>
          <p className="small">
            The app reads the files written by <code>src/oppreport.py</code>. Check that the API is running (
            <code>python -X utf8 app\run.py</code>) and that the data folder holds report_&lt;Team&gt;.json.
          </p>
          {!!teams?.length && (
            <p>
              <a className="btn" href={href({ key: teams[0].key })}>
                Open {teams[0].team}
              </a>
            </p>
          )}
        </div>
      ) : teams && teams.length === 0 ? (
        <div className="state">
          <h2>No reports in this folder yet</h2>
          <p>
            The app is reading <b>{info?.data_dir}</b> and found no report_&lt;Team&gt;.json.{" "}
            {info?.can_generate ? (
              <a href="#/new">Generate one for a team.</a>
            ) : (
              "Run src/oppreport.py for a team, or start the app with --data-dir on a folder with reports."
            )}
          </p>
        </div>
      ) : !current ? (
        <main aria-busy="true">
          <div className="skeleton" style={{ height: 60, width: "45%" }} />
          <div className="skeleton" style={{ height: 420 }} />
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="skeleton" />
          ))}
        </main>
      ) : (
        <>
          <div className="team-head" hidden={route.tab === "coach"}>
            <h1>{current.team}</h1>
            <div className="facts">
              <span>
                <b>{current.matches} matches</b>
                {current.period.replace(" to ", " – ")}
              </span>
              {here && providers && providers.length > 1 && (full || here.missing.length > 0) && (
                <a className="source-stamp" href={`#/${encodeURIComponent(current.key)}/evidence`}>
                  <b>{here.name} data</b>
                  {here.missing.length
                    ? `no ${here.missing.join(", ")} · grades from ${here.name}`
                    : `grades from ${here.name}`}
                </a>
              )}
              {current.provisional && (
                <span className="prov-flag">
                  Fewer than {current.min_matches ?? 8} matches: rough numbers, no ranks
                </span>
              )}
            </div>
            {!group && !full && route.tab !== "coach" && (
              <p className="view-note no-print">
                This page is part of the full report.{" "}
                <button type="button" className="linkish" onClick={() => setView("full")}>
                  Show every section
                </button>
              </p>
            )}
            {group && group[1].length > 1 && (
              <nav className="subnav no-print" aria-label={group[0]}>
                {group[1].map((k) => (
                  <a
                    key={k}
                    href={href({ key: current.key, tab: k })}
                    aria-current={
                      route.tab === k || (k === "build-up" && route.tab === "advanced") ? "page" : undefined
                    }
                  >
                    {TABS.find(([t]) => t === k)?.[1]}
                  </a>
                ))}
              </nav>
            )}
          </div>
          <main key={current.key}>
            {route.tab === "overview" && <Overview d={current} events={events} go={go} full={full} />}
            {(route.tab === "build-up" || route.tab === "advanced") && (
              <Families key={route.tab} d={current} phase={route.tab} events={events} family={route.family} go={go} />
            )}
            {route.tab === "restarts" && <Restarts d={current} events={events} go={go} />}
            {route.tab === "setpieces" && <SetPieces d={current} events={events} go={go} />}
            {route.tab === "threat" && <Threat d={current} events={events} go={go} />}
            {route.tab === "transitions" && <Transitions d={current} events={events} go={go} />}
            {route.tab === "defending" && <Defending d={current} />}
            {route.tab === "evidence" && <Evidence d={current} focus={route.family} />}
            {route.tab === "gameplan" && teams && <GamePlan d={current} teams={teams} events={events} full={full} />}
            {route.tab === "coach" && <CoachSheet d={current} />}
            {route.tab === "goals" && <Goals d={current} events={events} />}
            {route.tab === "matchups" && <Matchups d={current} />}
            {route.tab === "compare" && teams && <Compare d={current} teams={teams} events={events} />}
            {route.tab === "tracking" && <TrackingLab />}
            {route.tab === "review" && <Review d={current} events={events} />}
            {route.tab === "clips" && (
              <Clips
                d={current}
                kind={current.clips.includes(route.kind) ? route.kind : "sequences"}
                family={route.family}
                events={events}
                setFilter={(kind, family) => {
                  location.hash = href({ key: current.key, tab: "clips", kind, family });
                }}
              />
            )}
          </main>
        </>
      )}
      {tour && (
        <button
          type="button"
          className="tour-pill no-print"
          onClick={() => setTour(false)}
          aria-label="Stop the presentation tour"
        >
          Tour · {TABS.find(([k]) => k === route.tab)?.[1]}{" "}
          <span className="bar-t" key={route.key + route.tab}>
            <i style={{ "--tour": `${TOUR_MS}ms` } as React.CSSProperties} />
          </span>{" "}
          Esc to stop
        </button>
      )}
      <footer>
        <span>Master's thesis prototype · descriptive only</span>
        <span>Data: {info?.attribution ?? "StatsBomb Open Data (non-commercial licence)"}</span>
      </footer>
    </>
  );
}
