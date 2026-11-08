# Outreach Copilot — Design System

> **Status: BOTH DIRECTIONS IN BUILD (approved 2026-11-05).** The user chose to build Direction A "The card file" (`/a`) and Direction B "The checked proof" (`/b`) side by side on one shared data layer and one backend, then keep the better one. Sections 1–8 describe A; section 9 describes B. Shared rules (sentence case, motion, accessibility, the Never list) apply to both.

Product truth lives in `PRODUCT.md`. This file holds durable visual decisions only.

## 1. Direction in one paragraph

Sales has always kept prospects on cards: a ruled index card per person, a coloured tab on the ones that matter, a red rule under the name. Outreach Copilot is that card file made honest by evidence. The shell and controls are standard, quiet product UI; the world contributes only **type, palette, density and one signature move**: **the ruled prospect card**. Verified facts are set on the card's blue ruling, each with its source on the same line; the recommended hook carries the card file's index tab; uncertain and excluded evidence is visibly off the ruling. Everything else gets out of the way.

**Mode:** Operate (people work in it; desktop ~1440 and laptop ~1024; no dedicated phone layout).

## 2. Colour

Strategy: **Restrained, one hue ladder** (Taste `accent-ladder`, hue taken from the card's printed ruling instead of the dealt raspberry). Colour lives on data, selection and state, never on chrome. Target ≤ 6% coloured pixels.

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#f3f5f6` | Page and sidebar ground ("drawer steel": cool, low-chroma) |
| `--surface` | `#ffffff` | Cards, panels, inputs (card stock) |
| `--raised` | `#eef1f3` | Hover fill in lists, skeleton bars, segmented track |
| `--active` | `#e6eaed` | Active nav pill, selected row in a list driving a pane |
| `--border` | `#e1e5e8` | Panel and card edges (1px) |
| `--rule` | `#edf0f2` | Table row rules |
| `--control` | `#c8cfd5` | Input and select borders (one step stronger) |
| `--text` | `#151a1e` | Primary ink |
| `--muted` | `#59636c` | Secondary text (≥ 4.5:1 on white and ground) |
| `--primary` | `#151a1e` | The one filled button per screen (near-black, white label) |
| `--accent` | `#2a6f9e` | **Ruling blue**: full strength on small marks only: recommended-hook tab, top-signal score bar, active nav icon, focus ring, links in evidence |
| `--accent-soft` | `#edf5fa` | Tint areas: selected signal row, "Needs you" nav row |
| `--accent-track` | `#d6e6f1` | **The ruling**: card line rules, score-bar tracks |
| `--accent-ink` | `#183f5c` | Text on accent tints |
| `--index-red` | `#c8402f` | **Identity only**: the 2px rule under the prospect's name on the card. Never a state, never a button |
| `--positive` | `#237a4b` | Positive text; pill `#dcfae5` / `#04250e` |
| `--warning` | `#92400e` | Warning text; pill `#fffbeb` / `#92400e`, border `#fde68a` |
| `--negative` | `#b42a2a` | Error text and icon; pill `#ffedea` / `#831c1e` |

Evidence states (one mark per row, pale pill + dark ink of the same hue):
Verified = positive pair · Uncertain = neutral (`#eef1f3`/`#374151`) · Disputed = warning pair · Rejected = neutral, text struck through · Sensitive = negative pair.

## 3. Type

**Public Sans** (one family; the US government's open-source form face, derived from Franklin: the vernacular of forms and cards, not a kit default). Loaded with `next/font/google`, `font-display: swap`. Tabular figures (`tnum`) verified before build.

| Role | Size / line | Weight |
|---|---|---|
| Page title (h1) | 24 / 32 | 600 |
| Section / card title | 16 / 24 | 600 |
| Draft body (writing) | 16 / 26 | 400 |
| Body, nav, cells | 14 / 20 | 400 (500 for emphasis) |
| Labels, meta, table headers | 12 / 16 | 400–500 |
| Score figures | 14 / 20 tabular | 600 |

Rules: sentence case everywhere (resolves the Vercel "Title Case" guideline in favour of Frontend Design, Taste and Impeccable); tracking 0; no uppercase labels; no monospace except run IDs (`ui-monospace`). Ellipsis `…`, curly quotes, `Intl.DateTimeFormat` / `Intl.NumberFormat` for dates and numbers. No middle-dot meta strings, no `→` appended to buttons.

## 4. Space, radius, depth

- 4px base. Gap **16**; page padding **24–32**; card padding **20**; ruling pitch **28** (7 modules); table row **44**; nav row 32 on a 34 pitch; controls **34** (form inputs **38**).
- Radius (tight pair): card **8**, control **6**, chip **4**, prospect card **6** with a square-topped index tab.
- Depth: **no shadow at rest**; a 1px border *or* a tone step, never both. Floating layers only (menu, toast, dialog): `0 8px 24px rgba(21,26,30,.12)` + 1px `--border`.

## 5. Shell

Open plane (Taste): a labelled 232px sidebar on the page ground, separated by one 1px hairline; **no top bar**. Top of sidebar: the mark (a small index card with a ruling-blue tab and red rule, drawn in SVG) and "Outreach Copilot". Nav: **New prospect** (primary destination), **Prospects** (history). A **Needs you** group lists runs paused for input (identity, conflict, context, judgment, review) with a count only because it is a queue needing action. Bottom: API status (live from `/health`) and today's usage (from `/usage`). Canvas fluid with 32px gutters, content max ~1280px.

## 6. Components (principles)

- **Buttons:** primary near-black, secondary white with 1px `--control` border, tertiary text. One primary per screen. 34px. Press `scale(0.97)` 160ms.
- **Inputs:** label above (14/500), 38px, white, 1px `--control`, focus = 2px `--accent` ring offset 1px. Helper/limit text tied with `aria-describedby`; errors inline, focus first error on submit.
- **Tabs:** underline tabs on a full-width 1px rule; 2px ink indicator.
- **Tables:** 12px grey sentence-case headers, no band, 1px row rules, numbers right-aligned tabular, one status mark per row, no zebra.
- **Prospect card (signature):** white, 6px radius, 1px border; name + title on top, 2px `--index-red` rule; verified facts on 28px ruling lines (`--accent-track`), source domain + date right-aligned on the same line, quote one click away; uncertain items set below the ruling in `--muted`; excluded struck through; recommended hook carries the blue index tab.
- **Workflow line (progress):** the run drawn as one line with stations (identity → three research branches that split and rejoin → verify → rank → draft ⇄ quality → review); optional stations (targeted check, broaden) appear only when taken. Real node states only: done, current, waiting for you, skipped, failed. No percentages.
- **Toasts:** bottom-right, `aria-live="polite"`, same words as the action ("Draft approved").
- **Empty / loading / error:** frame and header stay; skeleton bars at real size, no shimmer; errors inside the failing block with what failed + Retry.

## 7. Motion

Emil Kowalski rules: motion is feedback or state, never decoration; nothing performs an entrance on page load.

- Easing: `--ease-out: cubic-bezier(.23,1,.32,1)`; `--ease-in-out: cubic-bezier(.77,0,.175,1)`.
- Durations: press 120–160ms; hover/colour 150ms `ease`; popovers 180ms; panels/sheets 220ms; never > 300ms for UI.
- Properties: `transform` and `opacity` only; never `transition: all`. Popovers scale from their trigger (`0.97 → 1` + fade); never from `scale(0)`.
- The current workflow station shows a small rotating ring (linear, 900ms); a newly completed station fills with a 180ms ease-out. A new "Needs you" item stays marked until opened.
- Hover effects gated by `@media (hover: hover) and (pointer: fine)`. No animation on keyboard-triggered actions. `prefers-reduced-motion`: remove movement, keep opacity/colour changes.

## 8. Never

Gradients, glass, glows, icons in tinted squares, KPI tiles with icons, sparklines, emoji, violet/indigo, cream + terracotta, a dark/saturated sidebar, uppercase tracked labels, rows of identical cards, fake progress percentages, invented data, a send button.

## 9. Direction B — "The checked proof" (`/b`)

A fact-checker's galley proof: every factual phrase that has been checked is marked, and its source hangs in the margin beside the exact line it supports. The world contributes type, palette, density and one signature move: **claims highlighted like a checked proof, with source notes keyed into a right-hand margin** (the discipline donated by the centre-rail reference challenger, without its cream paper, serif chrome or vermilion).

**Colour — achromatic ledger** (Taste `achromatic-ledger`). Chrome is ink only; colour budget < 2%.

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#f5f5f3` | Galley grey (neutral, saturation < 3%, not cream) |
| `--surface` | `#ffffff` | The proof sheet, panels, inputs |
| `--raised` | `#ececea` | Hover, skeleton, secondary button fill |
| `--active` | `#e4e4e1` | Active nav item, selected row |
| `--border` | `#e3e3e0` | Sheet and panel edges |
| `--rule` | `#eeeeec` | Row rules |
| `--control` | `#cfcfcb` | Input borders |
| `--text` | `#111111` | Ink |
| `--muted` | `#5e5e5a` | Secondary text (≥ 4.5:1) |
| `--primary` | `#111111` | The one filled button |
| `--accent` | `#1d5fbf` | **Proof blue**: source keys, links, focus ring, the main data mark |
| `--accent-soft` | `#eef3fb` | Selected claim / source pairing |
| `--mark` | `#fff1a8` | **Checker's highlight**: background behind verified claim text only (ink on top, ≥ 12:1) |
| `--mark-strong` | `#f2d43d` | Underline of the highlight when its source note is focused |
| status | as section 2 | positive / warning / negative pill pairs |

**Type.** UI in **Geist** (Taste-dealt, workhorse grotesk); **Source Serif 4** for one job only: the email text in the Draft Studio and the claim text on the proof (16/26). Geist Mono only for run IDs. Sizes 12 / 14 / 16 / 24, weights 400 / 500 / 600.

**Shell — no sidebar.** A 52px top bar on the ground: the mark (a folded proof corner with a check, in ink) and "Outreach Copilot" on the left; **New prospect**, **Prospects** links; a "Needs you" count link; API status on the right. Below it, a centred working column (max 1180px) on a white proof sheet with a 1px border and 10px radius, inset on the galley ground. Inside the sheet: a text column (~720px) plus a 300px margin column for source notes and apparatus.

**Signature components.**
- *Proof claims:* each verified claim is set in serif with the `--mark` highlight and a small proof-blue key (1, 2, 3 — data, the claim's order) linking to its note in the margin (domain, date, credibility, quote on expand). Uncertain claims sit unhighlighted in muted ink with "Not verified" in the margin; excluded claims are struck through.
- *Proofing checklist (progress):* the workflow as a vertical checklist in the text column with a check mark entering the margin as each stage completes; parallel research branches indent under one parent line; optional stages appear only when taken.
- *Draft proof:* the email in serif with every claim the draft used highlighted and keyed to its source in the margin; quality checks listed in the margin as checker's notes.

Radius: sheet 10, panel 8, control 6, chip 4. No shadow at rest. Motion: identical rules to section 7.
