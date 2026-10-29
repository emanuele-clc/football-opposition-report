/* Data provider of this page: StatsBomb or Wyscout, never mixed. Chosen in the top bar; kept in a cookie so links, images
   and downloads ask the backend for the same provider as the page's own fetches (which also send the X-Provider header).
   ?provider=wyscout in the URL overrides the cookie. Switching reloads the page, so no list or grade read for one provider
   survives into the other. */
export type ProviderId = "statsbomb" | "wyscout";

const read = (): ProviderId => {
  const q = new URLSearchParams(location.search).get("provider");
  if (q === "statsbomb" || q === "wyscout") return q;
  const c = document.cookie.match(/(?:^|;\s*)provider=(statsbomb|wyscout)/);
  return (c?.[1] as ProviderId) ?? "statsbomb";
};

export const PROVIDER: ProviderId = read();

const remember = (id: ProviderId) => {
  document.cookie = `provider=${id}; path=/; max-age=31536000; samesite=lax`;
};
remember(PROVIDER);

/* Reload on the other provider, on the same team and section when that team is there too. */
export async function switchProvider(id: ProviderId, teamKey: string, tab: string) {
  if (id === PROVIDER) return;
  let hash = "#/";
  try {
    const r = await fetch("/api/teams", { headers: { "X-Provider": id } });
    const teams: { key: string }[] = r.ok ? await r.json() : [];
    if (teamKey && teams.some((t) => t.key === teamKey))
      hash = `#/${encodeURIComponent(teamKey)}/${tab === "clips" || tab === "new" ? "overview" : tab}`;
    else if (teams.length) hash = `#/${encodeURIComponent(teams[0].key)}/overview`;
  } catch {
    /* the app falls back to the first team */
  }
  remember(id);
  const u = new URL(location.href);
  u.searchParams.delete("provider");
  u.hash = hash;
  history.replaceState(null, "", u.toString());
  location.reload();
}
