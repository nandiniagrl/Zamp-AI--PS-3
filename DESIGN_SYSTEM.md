# Outreach Copilot — Design System: "The checked proof"

> **Status:** chosen by the user on 2026-11-10 after both directions were built side by side (Phase 12). Direction A "The card file" was removed. Product truth lives in `PRODUCT.md`; this file holds durable visual decisions.

## 1. Direction

A fact-checker's galley proof. Every factual phrase that has been checked is marked, and its source hangs in the margin beside the exact line it supports. The shell and controls are quiet, standard product UI; the world contributes only **type, palette, density and one signature move**: **claims highlighted like a checked proof, keyed by number to source notes in a right-hand margin.**

Mode: Operate (people work in it). Supported widths: desktop ~1440px and laptop ~1024px; no dedicated phone layout.

## 2. Colour — achromatic ledger

Chrome is ink only. Colour is reserved for the checker's highlight, proof-blue source keys, and status. Colour budget under 2% of the screen.

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#f5f5f3` | Galley grey page ground (neutral, not cream) |
| `--surface` | `#ffffff` | The proof sheet, panels, inputs |
| `--raised` | `#ececea` | Hover, skeletons, segmented track |
| `--active` | `#e4e4e1` | Active nav item |
| `--border` | `#e3e3e0` | Sheet and panel edges |
| `--rule` | `#eeeeec` | Row rules, sheet section dividers |
| `--control` | `#cfcfcb` | Input borders |
| `--text` | `#111111` | Ink |
| `--muted` | `#5e5e5a` | Secondary text (≥ 4.5:1) |
| `--primary` | `#111111` | The one filled button per screen |
| `--accent` | `#1d5fbf` | Proof blue: source keys, links, focus ring, check marks |
| `--accent-soft` / `--accent-track` / `--accent-ink` | `#eef3fb` / `#dbe5f5` / `#163e78` | Tints for selection and the running ring |
| `--mark` | `#fff1a8` | Checker's highlight: **the hook** (and "Needs you" counts) |
| `--mark-soft` | `#fff8d6` | Other usable verified claims (selective highlighting keeps the hook legible) |
| status pills | positive `#dcfae5/#04250e`, warning `#fffbeb/#92400e` + `#fde68a`, negative `#ffedea/#831c1e`, neutral `#ececea/#3d3d3a` | Pale tint + dark ink of the same hue |

Rules: sensitive or unverified claims are never highlighted; one status mark per row; red only on a failing or sensitive fact.

## 3. Type

- **Geist** for all UI (400 / 500 / 600). Sizes 12 / 13 / 14 / 16 / 24; title 24/600 with −0.015em tracking.
- **Source Serif 4** for one job: claim text on the proof and the email in the Draft Studio (16–17px, 26–28px leading).
- **Geist Mono** only for IDs. Tabular figures on every number.
- Sentence case everywhere; no uppercase labels, no eyebrows, no middle-dot meta strings, `…` for ellipses, curly quotes, `Intl` for dates and numbers.

## 4. Space, radius, depth

4px base; sheet padding 40px horizontal; margin column 280–300px with a 1px rule; controls 34px (inputs 38px). Radius: sheet 10, panel 8, control 6, chip 4. No shadow at rest; floating layers (toasts) only: `0 8px 24px rgba(21,26,30,.12)` + 1px border.

## 5. Shell

No sidebar: a 52px top bar on the ground — the mark (a folded proof corner with a highlight and a proof-blue tick) and "Outreach Copilot"; **New prospect**, **Prospects**, **Needs you** (count only because it is a queue needing action); token/credit usage and API status on the right. Below it a centred column (max 1180px) holding the white proof sheet.

## 6. Signature components

- **Proof claims (Evidence tab):** verified claims in serif; the hook in `--mark` with a black "Hook" tag, other usable claims in `--mark-soft`; each keyed with a proof-blue number to its margin note (domain link, date, credibility, quote on demand). Sensitive claims: muted, "Sensitive: never used". Unverified: plain, with the verifier's reason in the margin; rejected ones struck through.
- **Proofing checklist (progress):** each workflow stage as a row with a check mark, the latest report beneath, the time in a right column; the three research branches nest under one line; optional stages (recheck, broaden) appear only when taken; pauses appear as a highlighted **Query** at the top of the sheet.
- **Draft proof (Draft Studio):** the email in serif with each sentence that carries a cited claim highlighted and keyed to its source; "Edit text" switches the column to an editor; checker's notes (quality results) in the margin; actions in a bar at the sheet's foot.

## 7. Components

Buttons: primary near-black, secondary white with 1px border, ghost text; press `scale(0.97)`. Inputs: label above, hint and error tied with `aria-describedby`, focus = proof-blue border + 3px tint ring. Tabs: underline on a full-width rule. Tables: 12px grey sentence-case headers, 1px row rules, numbers right-aligned. Empty / loading / error: frame stays, skeleton bars at real size, errors inline with a Retry.

## 8. Motion

Feedback and state only; nothing animates on page load. `--ease-out: cubic-bezier(.23,1,.32,1)`; press 160ms, colour 150ms, disclosure fade 180ms; spinner 900ms linear. Transform and opacity only; hover gated to real pointers; `prefers-reduced-motion` removes movement.

## 9. Dark mode (added 2026-11-10)

A toggle in the top bar (moon / sun icon, labelled "Switch to dark mode" / "Switch to light mode"). **Light is the default and is unchanged** — light mode sets no theme attribute; dark sets `data-theme="dark"` on `<html>`. The choice is saved per browser and applied by an inline `<head>` script before first paint (no flash); `color-scheme` and `theme-color` follow it. Switching is instant: colour transitions are suppressed for that frame.

Dark follows Taste's dark-screen rules: true neutral darks (no navy or slate), surfaces separated by a lightness step rather than shadows, inverted primary, two greys far enough apart, status inks lifted for contrast. Every text pair was measured at ≥ 4.5:1 (lowest: placeholder 5.31:1).

| Token | Dark | | Token | Dark |
|---|---|---|---|---|
| `--ground` | `#0e0e0d` | | `--accent` | `#78a6f0` |
| `--surface` (sheet) | `#171716` | | `--accent-soft` / `-track` / `-ink` | `#172235` / `#24395a` / `#c4d6f6` |
| `--raised` / `--active` | `#222220` / `#2a2a28` | | `--mark` (hook) / `--mark-soft` | `#5a4b12` / `#2f2a16` |
| `--border` / `--rule` / `--control` | `#2b2b29` / `#232321` / `#4a4a47` | | `--positive` / `--warning` / `--negative` | `#5fd08f` / `#e8b04b` / `#f37a7a` |
| `--text` / `--muted` / `--placeholder` | `#f1f1ee` / `#a9a9a4` / `#8c8c87` | | pills (bg/ink) | neutral `#2a2a28/#dcdcd8`, positive `#13301f/#7fe0a6`, warning `#332709/#f2c35b`, negative `#3b1719/#ffa3a3` |
| `--primary` / `--primary-ink` | `#f1f1ee` / `#111111` (inverted) | | `--seg-on` / `--on-accent` | `#33332f` / `#0e0e0d` |

Rule for new UI: never hard-code a colour in a component — use a token, so both themes stay correct.

## 10. Never

Gradients, glass, glows, icons in tinted squares, sparklines, emoji, violet/indigo, cream + terracotta, uppercase tracked labels, fake progress percentages, invented data, highlighting anything unverified or sensitive, a send button.
