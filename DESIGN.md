---
name: Automated Football Opposition Report
description: A local opposition-report app laid out as a sticker album; every finding is a numbered sticker on a night-blue board.
colors:
  board: "#121a33"
  board-deep: "#0b1124"
  board-raised: "#1a2446"
  on-board: "#ffffff"
  on-board-2: "#c9d1ea"
  on-board-3: "#98a3c7"
  sticker: "#ffffff"
  sticker-ink: "#121a33"
  sticker-ink-2: "#4b5574"
  yellow: "#ffd23f"
  sky: "#3fb7f5"
  lime: "#7ed957"
  coral: "#ff5a4e"
  lilac: "#c79bff"
  pitch: "#163a2a"
  pitch-band: "#19412f"
  them: "#ff8a80"
  caution: "#ffb547"
  board-light: "#e8ecf6"
  board-raised-light: "#dde3f1"
  pitch-light: "#e3efe6"
  trail-light: "#1d3fae"
  them-light: "#c2382d"
  caution-light: "#a85d00"
  sticker-wash: "#eef1f8"
  sticker-field: "#f6f7fb"
  bar-ink: "#ffffff"
  bar-ink-2: "#c9d1ea"
  ink-hover: "#26335f"
  legend-pass: "#b8920e"
  legend-them: "#d6483c"
  flag-soft: "#ffe3c2"
typography:
  display:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "clamp(36px, 3.8vw, 56px)"
    fontWeight: 900
    lineHeight: 0.95
    letterSpacing: "0.005em"
    fontVariation: "'wdth' 62"
  headline:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 900
    lineHeight: 0.95
    letterSpacing: "0.005em"
    fontVariation: "'wdth' 62"
  title:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 900
    lineHeight: 0.95
    letterSpacing: "0.005em"
    fontVariation: "'wdth' 62"
  figure:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "25px"
    fontWeight: 900
    lineHeight: 1
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 62"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum' 1"
  small:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "11.5px"
    fontWeight: 750
    lineHeight: 1.2
    letterSpacing: "0.06em"
  mono:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  tip: "6px"
  tab: "8px"
  pitch: "9px"
  field: "10px"
  panel: "12px"
  sticker: "14px"
  pill: "999px"
spacing:
  gutter: "clamp(16px, 2.2vw, 32px)"
  xs: "6px"
  sm: "12px"
  md: "16px"
  lg: "28px"
  section: "60px"
components:
  sticker:
    backgroundColor: "{colors.sticker}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.sticker}"
    padding: "10px"
  sticker-padded:
    backgroundColor: "{colors.sticker}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.sticker}"
    padding: "18px 18px 16px"
  number-tab:
    backgroundColor: "{colors.coral}"
    textColor: "{colors.sticker-ink}"
    typography: "{typography.title}"
    rounded: "{rounded.tab}"
    padding: "5px 11px 4px"
  button-primary:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.on-board}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  control:
    backgroundColor: "{colors.sticker}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 12px"
  control-primary:
    backgroundColor: "{colors.sticker-ink}"
    textColor: "{colors.sticker}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 12px"
  nav-pill:
    backgroundColor: "transparent"
    textColor: "{colors.on-board-2}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
  nav-pill-active:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
  filter-pill:
    backgroundColor: "transparent"
    textColor: "{colors.on-board-2}"
    rounded: "{rounded.pill}"
    padding: "7px 15px"
  filter-pill-pressed:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    padding: "7px 15px"
  chip:
    backgroundColor: "{colors.board-raised}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  rank-badge:
    backgroundColor: "{colors.sticker-ink}"
    textColor: "{colors.yellow}"
    typography: "{typography.figure}"
    rounded: "{rounded.field}"
    padding: "7px 0 6px"
  field-select:
    backgroundColor: "{colors.board-raised}"
    textColor: "{colors.on-board}"
    rounded: "{rounded.field}"
    padding: "8px 34px 8px 12px"
  note:
    backgroundColor: "{colors.board-raised}"
    textColor: "{colors.on-board}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  team-select:
    backgroundColor: "{colors.sticker}"
    textColor: "{colors.sticker-ink}"
    rounded: "{rounded.pill}"
    padding: "8px 36px 8px 16px"
---

# Design System: Automated Football Opposition Report

Scope: this system covers the local web app in `app/frontend` (Vite + React, hand-built SVG). The static HTML sheets written by the pipeline (`src/report/*.py` and `src/oppreport.py` outputs: `report_`, `prep_`, `restarts_`, `setpieces_`, `transitions_`, `review_`) are out of scope. They keep their own print styling, and nothing here applies to them.

## Overview

**Creative North Star: "The Sticker Album"**

Each finding is a numbered sticker on a night-blue album board. A sticker is a white card with a rounded corner, a thin white frame around its content, and one saturated ribbon colour that identifies it. Its front shows the finding: a replay on the pitch, a family code with its share, or a sentence with a rank badge. Its back holds the numbers: intervals, per-match spread, stability. The board stays quiet so the stickers and the pitch carry the screen. The layout is dense but readable at a glance: big italic condensed figures, short plain sentences, and every caution set out in its own visible note.

The app is built to move. Possessions replay pass by pass on the pitch, family stickers flip over, rank dots slide when the team changes, and sections change with a short view transition. All of this motion goes away under reduced motion. The dark board is for the video room and the projector. The light theme turns the board into a pale album page with ink keylines around the stickers, and the print stylesheet removes motion and controls, so a page prints in black and white.

**Key Characteristics:**
- Night-blue board, white stickers, one ribbon colour per sticker.
- Five ribbon colours used as an ordered set; yellow also marks the live/selected state.
- One typeface (Archivo variable): extra-condensed black italic uppercase for names and figures, regular width for sentences, tabular figures everywhere.
- One pitch geometry (120 x 80, attacking left to right, mown bands) for every chart.
- Springy motion on stickers, ease-out on data, nothing under reduced motion.

## Colors

The palette is a dark navy board with white cards and five saturated sticker ribbons. Each ribbon has a job, and none is decoration.

### Primary
- **Album Yellow** (yellow): the live/selected colour. Used for the brand wordmark, the active section pill, pressed filters, the primary button, the focus ring, text selection, the current team's dot on rank tracks, the replay pass trail in the dark theme, and the first family ribbon.

### Secondary
- **Sky Ribbon** (sky): the second family ribbon, the comparison team in Compare (its values and its dot), info notes, and the numbered review questions.
- **Lime Ribbon** (lime): the third family ribbon, "ok" notes, and the "yes" verdict.
- **Coral Ribbon** (coral): the fourth family ribbon, the default number-tab colour, shots on the pitch, the last-5-matches marker on intervals, and the "no" verdict.
- **Lilac Ribbon** (lilac): the fifth family ribbon only.

### Tertiary
- **Pitch Green** (pitch, with pitch-band stripes every 10 m): the pitch surface. Chalk lines are white at 34% (`rgba(255,255,255,0.34)`).
- **Opponent Salmon** (them): opponent actions in replays.
- **Caution Amber** (caution): caution note tags and the flagged-rank asterisk.

### Neutral
- **Night Board** (board): the page background.
- **Deep Bar Navy** (board-deep): the sticky top bar (dark in both themes) and the log panel.
- **Raised Board** (board-raised): notes, inputs, selects and skeletons on the board.
- **Board Line** (`rgba(201,209,234,0.16)`): row rules, pill outlines, track rails.
- **On-board text** in three steps (on-board, on-board-2, on-board-3): headings and values, secondary text, then table headers, scales and fine print.
- **Sticker White / Sticker Ink** (sticker, sticker-ink, sticker-ink-2): the card surface, its main text and its secondary text. Sticker Ink is the same navy as the board.

Light theme (`data-theme="light"`) swaps the board to board-light / board-raised-light. On-board text becomes ink, the pitch becomes pitch-light with green chalk lines, the replay trail becomes trail-light (cobalt), opponent becomes them-light, caution becomes caution-light, and stickers gain a 1.5px ink keyline (`rgba(18,26,51,0.2)`).

### Named Rules
**The Ribbon Order Rule.** Families and sticker series take ribbons in fixed order: yellow, sky, lime, coral, lilac, then repeat. A family's code is always printed on its ribbon, so colour is never the only cue.

**The Yellow Means Live Rule.** On chrome, yellow marks only what is selected, active, focused or "this team". Do not use it as a general highlight.

**The Ink-on-Ribbon Rule.** Text on any ribbon, chip, tag or yellow surface is Sticker Ink, never white.

## Typography

**Display Font:** Archivo Variable at width 62, italic, weight 900, uppercase (fallback Archivo, system-ui)
**Body Font:** Archivo Variable at normal width (same family)
**Label/Mono Font:** Archivo for labels; ui-monospace / Cascadia Mono / Consolas for logs and code only

**Character:** The display voice copies the name plate of a football sticker: compressed, slanted, heavy, all caps. Sentences use the same family at normal width, so the page reads as one voice. Body text uses tabular figures (`font-variant-numeric: tabular-nums`) so numbers line up.

### Hierarchy
- **Display** (900 italic, clamp(36px, 3.8vw, 56px), 0.95): the team name in the team header only.
- **Headline** (900 italic, 32px, 0.95; 27px under 620px): section headings and replay captions (clamp(22px, 2vw, 28px)). Empty and error states use 42px.
- **Title** (900 italic, 21px, 0.95): sub-section headings such as "Key points" and "Build-up families" (shown in accent-text: yellow on dark, ink on light), and the number tab.
- **Figure** (900 italic condensed, 19-36px): numbers that carry the finding. Rank values 25px, rank badges 25px, family code and share 36px on the sticker front, share strip 28px, duo values 26px, code cells 19px.
- **Body** (400, 15px, 1.5): sentences. Key-point emphasis is 800 at 18px. Long text is capped at 70ch.
- **Small** (400, 12.5-13.5px): captions, sticker sentences, footers, legends.
- **Label** (750, 11.5-12px, tracking 0.05-0.08em, uppercase): table headers, form field labels, rank group names, note tags. Every label names a column, a field or a group of rows. Labels are never decorative lines above a heading.

### Named Rules
**The Two Widths Rule.** Names and figures use condensed black italic. Sentences use regular width. Never set a sentence in the condensed voice or a headline figure in regular width.

**The Tabular Figures Rule.** Every number in the app uses tabular figures.

## Layout

The page has a full-width sticky top bar (minimum 64px high), a team header, and a main area with a fluid gutter of clamp(16px, 2.2vw, 32px) on both sides. Sections are 60px apart. Each section opens with a section head: the heading on the left and a short explanation (70ch max) or the controls on the right, wrapping when space runs out.

Grids in use: the hero (1.42fr / minmax(320px, 1fr), 28px gap), a split (1.25fr / 1fr), two equal columns, family stickers on an auto-fit grid (minimum 150px, 16px gap), and rank rows in two columns 44px apart. Stacks use 16px between items and the key-point list uses 14px.

Breakpoints: at 1680px icon buttons drop their text labels. At 1120px every multi-column layout becomes one column, the section pills wrap onto their own row and fade out on the right edge with a mask, and ranks become one column. At 620px rank tracks move onto their own line, the replay caption stacks vertically, and notes stack their tag above the text.

## Elevation & Depth

Depth here is a sticker lying on a board, with a soft drop shadow and no layers of glass. Stickers and floating elements share one lift shadow. The board itself is flat. Raised areas on the board (notes, inputs) are separated by tone (board-raised), not by shadow. Print removes all shadows.

### Shadow Vocabulary
- **Sticker lift** (`box-shadow: 0 1px 0 rgba(0,0,0,0.18), 0 14px 28px -16px rgba(0,0,0,0.65)`; light theme `0 1px 0 rgba(18,26,51,0.08), 0 10px 22px -16px rgba(18,26,51,0.45)`): every sticker, the share strip, the tour pill and track tooltips.
- **Tab drop** (`box-shadow: 0 2px 6px -1px rgba(0,0,0,0.35)`): the number tab sitting over the sticker's top edge.
- **Selected ring** (`box-shadow: var(--lift), 0 0 0 3px #ffd23f`): a selected family sticker. Inside the share strip, the selected segment gets an inset 3px ink ring instead.

### Named Rules
**The One Lift Rule.** There is one blurred lift shadow for everything that sits on the board. No hard offset shadows and no stacked elevation tiers.

## Shapes

Corners are rounded throughout, with a fixed radius for each kind of object: stickers 14px, notes and the share strip 12px, fields, badges and textareas 10px, pitch frames and video 9px, number tabs and share segments 8px, tooltips and the focus ring 6px. Everything interactive on the chrome (navigation, filters, buttons, chips, controls, segmented toggles) is a full pill (999px). Dots are circles: 34px numbered dots on key points and review questions, 10px team dots on rank tracks and an 18px dot for the current team. Lines on the pitch have round caps. Passes are solid with arrowheads, runs and failed passes are dashed, and shots are thick coral lines ending in a ring, so the line style tells the action apart even in black and white.

## Components

### Stickers (signature)
A white card on the board.
- **Corner Style:** 14px.
- **Background:** sticker white, sticker-ink text; in light theme an inset 1.5px ink keyline.
- **Shadow Strategy:** sticker lift (see Elevation).
- **Internal Padding:** 10px (the white frame around a pitch), or 18px 18px 16px for text stickers.
- **Number tab:** sits 13px above the top edge, 18px from the left, in the sticker's ribbon colour (coral by default), using the 21px condensed figure voice. It carries the sticker's identity: the family code, team name or set-piece kind.
- **Enter:** stickers rise 14px with a -0.8deg tilt over 560ms, staggered 70ms each.

### Family sticker (flip)
A button that turns over. The front has a 14px ribbon band, code and share at 36px, a mini pitch with the family's average start-to-end arrow in its ribbon colour, and one factual sentence. The back holds a definition list: share interval, duration, long passes, shot rate, per-match p10-p90, stability. Hover or focus rotates it (rotateY 180deg, 560ms spring, 900px perspective). When selected it gets a 3px yellow ring. Print hides the back.

### Pitch and Replay (signature)
One SVG pitch (viewBox based on 120 x 80) with stripes every 10 m and chalk lines at 0.4 stroke. The replay draws each action as it plays: passes extend in 500ms with ease-out, the ball eases to the next action, and the receiver's surname floats above it. It zooms to the area of play when the action covers only part of the pitch. Below it: a play/pause control (ink fill), previous/next, a scrubber, a clip count, a speed control (1x/2x/4x), a live line describing the current action, and a legend that tells actions apart by line style. Without event files it falls back to family lanes: average start-to-end bars in ribbon colours.

### Key point
A text sticker laid out as a three-column grid: a 34px numbered dot in the ribbon colour, a sentence with a bold 18px figure and a 12.5px context line, and a rank badge (ink tile, condensed yellow ordinal at 25px, "of N" in small text). On hover it lifts 2px with a -0.4deg tilt (280ms spring).

### Rank row
Label (with its 95% interval in small text), condensed value, a dot track, and the ordinal. Each team is a 10px dot on a 2px rail, and the current team is an 18px yellow dot ringed in board colour. Dots slide to their positions over 900ms when the team changes. Hover or arrow keys name a dot through a white tooltip.

### Share strip
A white tray 64px high with 5px padding. Its segments grow in proportion to share (flex-grow, 700ms ease-out), each in its ribbon colour with the code and share in condensed figures. The selected segment gets an inset ink ring.

### Buttons
- **Shape:** full pill (999px).
- **Primary:** yellow fill, ink text, 750 weight 14px, 10px 16px padding. On hover it lifts 1px (220ms spring).
- **Ghost:** transparent, on-board text, inset 1.5px board-line ring that brightens to on-board-3 on hover.
- **Controls (on stickers):** 36px high, white with a 1.5px sticker-line border that turns ink on hover. The primary control is filled ink (#26335f on hover).
- **Icon buttons (top bar):** 38px high, transparent, 1.5px pale outline that turns white on hover. Inline SVG icons at 17px. Labels hide below 1680px.
- **Disabled:** 40-45% opacity, not-allowed cursor.
- **Focus (everything):** 3px yellow outline, offset 3px.

### Chips and tags
- **Chip:** pill, ribbon background (board-raised when there is no ribbon), ink text 750 12.5px. Used for family codes in tables.
- **Note tag:** uppercase label pill (11px, 800, 0.06em) in the note's state colour: caution amber, ok lime, info sky.

### Notes
A raised-board panel (12px radius, 12px 14px padding, 14px text) with a state tag on the left. Inside a sticker the panel turns pale (#eef1f8). Notes carry every caution the pipeline produces. They are never hidden behind a toggle.

### Inputs / Fields
- **Style:** board-raised fill, 1.5px board-line border, 10px radius, on-board text 14.5px. Selects use a CSS chevron. Field labels sit above in the uppercase label style.
- **Focus:** the global 3px yellow outline.
- **Team select (top bar):** white pill with ink text 750 weight and an ink chevron.
- **Checkbox:** accent-color yellow, 17px.

### Navigation
The sticky deep-navy top bar holds: the brand in yellow condensed italic (26px, 22px on mobile), the team pill select, section links as pills (650 14px, pale text, 8% white on hover, solid yellow with ink text when current), and icon buttons. Below 1120px the links move to their own scrolling row with a fade-out on the right. Section changes use a view transition: the old page fades and moves up 6px in 150ms, and the new one rises 12px in 380ms.

### Tables
Right-aligned numbers, first column left-aligned. Rows are separated by board-line rules. Headers use the uppercase label style. Sortable headers use a CSS triangle. Hovered rows get a faint tint, and the selected row gets a 14% yellow wash. A wide table scrolls sideways, with yellow glows at its edges showing there is more to scroll.

## Do's and Don'ts

### Do:
- **Do** put every finding on a sticker: white card, 14px radius, sticker lift, a ribbon colour, and a number tab carrying its code.
- **Do** assign ribbons in the fixed order yellow, sky, lime, coral, lilac, and print the code on the ribbon every time.
- **Do** set names and figures in Archivo at width 62, 900 italic uppercase, and sentences in Archivo at regular width, with tabular figures.
- **Do** draw every spatial chart on the one 120 x 80 pitch, attacking left to right, and tell actions apart by line style (solid pass with arrowhead, dashed run, thick coral shot).
- **Do** use the springy curve `cubic-bezier(0.2, 1.3, 0.35, 1)` for sticker motion (flip, lift) and `cubic-bezier(0.16, 1, 0.3, 1)` for data motion (dots, bars, draws), and turn both off under `prefers-reduced-motion`.
- **Do** show cautions as visible notes with a state tag, next to the number they qualify.
- **Do** keep family labels as codes (B1, A2) with factual descriptions.

### Don't:
- **Don't** use yellow for decoration; it means selected, live, focused or "this team".
- **Don't** put white text on a ribbon, chip, tag or yellow surface.
- **Don't** build grey KPI cards or dense ruled dashboards. A number belongs on a sticker or a rank row, with its interval.
- **Don't** add hard offset shadows or extra elevation tiers. The one lift shadow is the only depth.
- **Don't** add uppercase labels above headlines. Uppercase labels name a column, a field, a group of rows or a note state, nothing else.
- **Don't** use glyph or emoji icons. Icons are inline SVG strokes at 15-17px.
- **Don't** rely on colour alone. Every ribbon carries its code, and every pitch line has a distinct line style.
