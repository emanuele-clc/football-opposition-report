/* Interface language (English, Italian, German) without touching every view: the app is written in English and a MutationObserver
   translates the rendered text with the dictionary in i18n-dict.ts. Text the dictionary does not know (team and player names, rare
   sentences) stays in English. Keys: '#' = a number (ordinal suffix allowed in '#th'), '{0}', '{1}'... = any text, itself translated.
   Long strings are tried whole, then sentence by sentence, then piece by piece around ' · '. */
import { DICT } from "./i18n-dict";

export type Lang = "en" | "it" | "de";
export const LANGS: [Lang, string][] = [
  ["en", "English"],
  ["it", "Italiano"],
  ["de", "Deutsch"],
];

const NUM = "(\\d+(?:[.,]\\d+)*)";
const SENTENCE = /(?<=[.?!])\s+(?=[A-Z0-9"'(])/;
type Template = { re: RegExp; kinds: ("n" | "t")[]; it: string; de: string; weight: number };
const exact = new Map<string, [string, string]>(); // plain keys and keys with numbers only (looked up after normalising numbers)
const templates: Template[] = [],
  generic: Template[] = [];
const add = (en: string, it: string, de: string) => {
  if (!en.includes("{")) {
    if (!exact.has(en)) exact.set(en, [it, de]);
    return;
  }
  const kinds: ("n" | "t")[] = [];
  const src = en
    .split(/(#th|#|\{\d+\})/)
    .map((p) => {
      if (p === "#th") {
        kinds.push("n");
        return "(\\d+)(?:st|nd|rd|th)";
      }
      if (p === "#") {
        kinds.push("n");
        return NUM;
      }
      if (/^\{\d+\}$/.test(p)) {
        kinds.push("t");
        return "((?:[^.]|\\.(?!\\s+[A-Z0-9]))+?)";
      } // any text, not across a sentence end ("opp. half" is fine)
      return p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    })
    .join("");
  const weight = en.replace(/#|\{\d+\}/g, "").length;
  (weight < 5 ? generic : templates).push({ re: new RegExp(`^${src}$`), kinds, it, de, weight });
};
for (const [en, it, de] of DICT) {
  add(en, it, de);
  // multi-sentence entries also count sentence by sentence, so a sentence found inside a longer text is still translated
  const [a, b, c] = [en, it, de].map((x) => x.split(SENTENCE));
  if (a.length > 1 && a.length === b.length && a.length === c.length) a.forEach((x, i) => add(x, b[i], c[i]));
}
for (const list of [templates, generic]) list.sort((a, b) => b.weight - a.weight);

const norm = (s: string) => s.replace(/\d+(?:[.,]\d+)*/g, "#").replace(/#(?:st|nd|rd|th)\b/g, "#th");
const fill = (out: string, nums: string[]) => {
  let i = 0;
  return out.replace(/#/g, () => nums[i++] ?? "#");
};

let lang: Lang = "en";
const cache = new Map<string, string | null>();

function apply(list: Template[], core: string, strict: boolean): string | null {
  for (const t of list) {
    const m = t.re.exec(core);
    if (!m) continue;
    const nums: string[] = [],
      txt: string[] = [];
    t.kinds.forEach((kind, i) => (kind === "n" ? nums : txt).push(m[i + 1]));
    // short generic keys ("{0} #", "{0}: #%") only when their text part is known
    if (strict && txt.some((x) => tr(x) === null)) continue;
    const out = fill(lang === "it" ? t.it : t.de, nums);
    return out.replace(/\{(\d+)\}/g, (_, i) => translate(txt[+i] ?? ""));
  }
  return null;
}

function lookup(core: string): string | null {
  const k = lang === "it" ? 0 : 1;
  const hit = exact.get(core);
  if (hit) return hit[k];
  if (/\d/.test(core)) {
    const n = exact.get(norm(core));
    if (n) return fill(n[k], core.match(/\d+(?:[.,]\d+)*/g) ?? []);
  }
  return apply(templates, core, false);
}

/** Translation of one string in the current language; the string itself when nothing is known. */
export function translate(s: string): string {
  return lang === "en" ? s : (tr(s) ?? s);
}

function tr(s: string): string | null {
  const c = cache.get(s);
  if (c !== undefined) return c;
  cache.set(s, null); // guards against a template calling back on the same text
  let out: string | null = null;
  const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s)!;
  const core = m[2].replace(/ {2,}/g, " ");
  if (/[A-Za-z]{2}/.test(core)) {
    out = lookup(core);
    // punctuation around a known piece: "(highest of 10)", ", reached the opponent half", "Corners:", "Clips →", "Share of long passes (30+):"
    for (const re of [/^([\s·,:;.(←↑→*]*)([\s\S]*?)([\s·,:;.)←→?]*)$/, /^([\s·,:;.←↑→*]*)([\s\S]*?)([\s·,:;.←→?]*)$/]) {
      if (out !== null) break;
      const p = re.exec(core)!;
      if (p[2] !== core && p[2]) {
        const r = lookup(p[2]) ?? apply(generic, p[2], true);
        if (r !== null) out = p[1] + r + p[3];
      }
    }
    if (out === null) out = pieces(core, SENTENCE);
    if (out === null) out = pieces(core, / · /, " · ");
    if (out === null) out = pieces(core, /;\s+/, "; ");
    if (out === null) out = pieces(core, /,\s+/, ", ", true);
    if (out === null) out = apply(generic, core, true);
    if (out !== null) out = m[1] + out + m[3];
  }
  cache.set(s, out);
  return out;
}

function pieces(core: string, sep: RegExp, joiner?: string, all = false): string | null {
  const parts = core.split(sep);
  if (parts.length < 2) return null;
  let any = false,
    missing = false;
  const done = parts.map((p) => {
    const r = tr(p);
    if (r === null) missing = true;
    else if (r !== p) any = true;
    return r ?? p;
  });
  return any && !(all && missing) ? done.join(joiner ?? " ") : null; // comma lists only when every item is known
}

/* ---- DOM side: runs of adjacent text nodes are translated together; the English original is kept to switch back. ---- */
const original = new WeakMap<Text, string>(); // what React wrote
const written = new WeakMap<Text, string>(); // what we wrote
const attrOrig = new WeakMap<Element, Map<string, [string, string]>>(); // attribute -> [original, what we wrote]
const ATTRS = ["title", "aria-label", "placeholder"];
const SKIP = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "TEXTAREA", "INPUT", "NOSCRIPT"]);
const skip = (el: Element | null): boolean => !el || SKIP.has(el.tagName) || !!el.closest("[translate='no']");

const orig = (t: Text) => {
  const w = written.get(t);
  if (w === undefined || w !== t.nodeValue) original.set(t, t.nodeValue ?? ""); // React changed it since our last write
  return original.get(t) ?? t.nodeValue ?? "";
};
const put = (t: Text, v: string) => {
  if (t.nodeValue !== v) t.nodeValue = v;
  written.set(t, v);
};

function translateRun(run: Text[]) {
  const src = run.map(orig);
  if (lang === "en") {
    run.forEach((t, i) => put(t, src[i]));
    return;
  }
  const whole = tr(src.join(""));
  if (whole !== null) {
    run.forEach((t, i) => put(t, i === 0 ? whole : ""));
    return;
  }
  run.forEach((t, i) => put(t, tr(src[i]) ?? src[i]));
}

function translateElement(el: Element) {
  if (skip(el)) {
    // the text typed in a field stays as it is, but its placeholder and label are interface text
    if ((el.tagName === "INPUT" || el.tagName === "TEXTAREA") && !el.closest("[translate='no']")) translateAttrs(el);
    return;
  }
  let run: Text[] = [];
  for (const n of Array.from(el.childNodes)) {
    if (n.nodeType === 3) {
      run.push(n as Text);
      continue;
    }
    if (run.length) {
      translateRun(run);
      run = [];
    }
    if (n.nodeType === 1) translateElement(n as Element);
  }
  if (run.length) translateRun(run);
  translateAttrs(el);
}

function translateAttrs(el: Element) {
  for (const a of ATTRS) {
    if (!el.hasAttribute(a)) continue;
    let o = attrOrig.get(el);
    if (!o) {
      o = new Map();
      attrOrig.set(el, o);
    }
    const cur = el.getAttribute(a) ?? "";
    const prev = o.get(a);
    if (!prev || cur !== prev[1]) o.set(a, [cur, cur]); // first visit, or React changed it
    const src = o.get(a)![0];
    const v = lang === "en" ? src : (tr(src) ?? src);
    if (cur !== v) el.setAttribute(a, v);
    o.set(a, [src, v]);
  }
}

let observer: MutationObserver | null = null;
const pending = new Set<Element>();
let scheduled = false;
const flush = () => {
  scheduled = false;
  observer?.disconnect();
  for (const el of pending) if (el.isConnected) translateElement(el);
  pending.clear();
  observe();
};
const queue = (el: Element | null) => {
  if (!el) return;
  pending.add(el);
  if (!scheduled) {
    scheduled = true;
    queueMicrotask(flush);
  }
};
const observe = () =>
  observer?.observe(document.documentElement, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ATTRS,
  });

export function setLanguage(next: Lang) {
  lang = next;
  cache.clear();
  document.documentElement.lang = next;
  if (!observer) {
    observer = new MutationObserver((records) => {
      for (const r of records) queue(r.type === "characterData" ? r.target.parentElement : (r.target as Element));
    });
  }
  observer.disconnect();
  translateElement(document.documentElement);
  observe();
}

export function storedLanguage(): Lang {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "en" || q === "it" || q === "de") return q;
  try {
    const s = localStorage.getItem("lang");
    if (s === "en" || s === "it" || s === "de") return s;
  } catch {
    /* private window */
  }
  const nav = (navigator.language || "en").slice(0, 2);
  return nav === "it" || nav === "de" ? nav : "en";
}

/** For tests: translate without a DOM (switches the language used by translate()). */
export function translateIn(s: string, to: Lang): string {
  if (to !== lang) {
    lang = to;
    cache.clear();
  }
  return translate(s);
}
