import React, { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { api, type Info, type TeamData, type TeamSummary } from "./api";
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
/* The top bar names the group, the row under the team name the section. The everyday path is Summary -> a phase -> Clips;
   the rest sits under More. */
const GROUPS: [string, string[]][] = [
  ["Summary", ["overview", "gameplan", "coach", "evidence"]],
  ["With the ball", ["build-up", "threat", "restarts", "setpieces", "goals"]],
  ["Without the ball", ["transitions", "defending"]],
  ["Clips", ["clips"]],
  ["More", ["compare", "matchups", "review", "tracking"]],
];
const groupOf = (tab: string) =>
  GROUPS.find(([, t]) => t.includes(tab === "advanced" ? "build-up" : tab === "coach" ? "gameplan" : tab)) ?? GROUPS[0];
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

  const current = route.key === "new" ? null : data && data.key === route.key ? data : null;
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
              aria-current={groupOf(route.tab)[0] === label && route.key !== "new" ? "true" : undefined}
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="bar-actions">
          {info?.can_generate && (
            <a
              className="icon-btn"
              href="#/new"
              aria-current={route.key === "new" ? "page" : undefined}
              aria-label="Add a team"
            >
              {Icon.plus}
              <span>Add team</span>
            </a>
          )}
          <button
            className="icon-btn"
            type="button"
            onClick={() => {
              if (!tour && route.key !== "new" && !TOUR.includes(route.tab))
                location.hash = href({ key: route.key, tab: "overview" });
              setTour(!tour);
            }}
            aria-pressed={tour}
            aria-label={tour ? "Stop the presentation tour" : "Start the presentation tour"}
          >
            {Icon.tour}
            <span>Tour</span>
          </button>
          <label className="icon-btn lang" translate="no" title="Language · Lingua · Sprache">
            {Icon.globe}
            <span className="lang-code">{lang.toUpperCase()}</span>
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as Lang)}
              aria-label="Language · Lingua · Sprache"
            >
              {LANGS.map(([k, name]) => (
                <option key={k} value={k}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="icon-btn"
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? Icon.sun : Icon.moon}
          </button>
          <button className="icon-btn" type="button" onClick={() => print()} aria-label="Print this page">
            {Icon.print}
            <span>Print</span>
          </button>
        </div>
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
              {current.provisional && (
                <span className="prov-flag">
                  Fewer than {current.min_matches ?? 8} matches: rough numbers, no ranks
                </span>
              )}
            </div>
            {groupOf(route.tab)[1].length > 1 && (
              <nav className="subnav no-print" aria-label={groupOf(route.tab)[0]}>
                {groupOf(route.tab)[1].map((k) => (
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
            {route.tab === "overview" && <Overview d={current} events={events} go={go} />}
            {(route.tab === "build-up" || route.tab === "advanced") && (
              <Families key={route.tab} d={current} phase={route.tab} events={events} family={route.family} go={go} />
            )}
            {route.tab === "restarts" && <Restarts d={current} events={events} go={go} />}
            {route.tab === "setpieces" && <SetPieces d={current} events={events} go={go} />}
            {route.tab === "threat" && <Threat d={current} events={events} go={go} />}
            {route.tab === "transitions" && <Transitions d={current} events={events} go={go} />}
            {route.tab === "defending" && <Defending d={current} />}
            {route.tab === "evidence" && <Evidence d={current} focus={route.family} />}
            {route.tab === "gameplan" && teams && <GamePlan d={current} teams={teams} events={events} />}
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
        <span>Data: StatsBomb Open Data (non-commercial licence){info ? ` · ${info.data_dir}` : ""}</span>
      </footer>
    </>
  );
}
