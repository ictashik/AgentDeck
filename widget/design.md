# AgentDeck — Notch Widget Design Philosophy

Governs color and display for the software-only surface: a notch-anchored menu bar widget
that works standalone (MPK disconnected) and as the deck's on-screen mirror (MPK connected,
replacing native notifications). Colors, density, and motion only — not architecture or code.

---

## 1. Core philosophy

**High density, not airy.** This is not a typical macOS widget. Typical widgets optimize for
friendliness: big padding, soft shadows, one piece of information per card. This widget
optimizes for the opposite — the most state per pixel that's still legible at a glance,
because the entire point is watching 8 things at once without switching windows or scrolling.
Think instrument panel or DAW mixer strip, not Notification Center card. The physical MPK is
already dense (8 pads in a 4×2 grid, no wasted space); the software surface should feel like
the same object, not a decorated wrapper around it.

**Hardware/software color parity.** One color vocabulary, period. The color that means
"waiting on you" on pad 3 is the exact same color for slot 3 in the notch. No separate palette
to learn depending on which surface you happen to be looking at.

**The notch as an extension, not an icon.** Don't build "a menu bar icon that opens a panel."
Build something that visually continues the physical notch cutout — same near-black, same
corner radius language, opaque and fused to the hardware in its resting state. It should look
like the notch grew an extra 8 pixels, not like an app installed something next to it.

**Blink means actionable, solid means informational.** This is the one rule that disciplines
every other decision in this doc. If a state blinks, you can resolve it in one tap from the
deck (or the widget) without going anywhere else. If it's solid, it's telling you something,
not asking you something — go look at the IDE if you want to act on it. Never blink a state
the user can't resolve from here; never leave an actionable state solid.

**Pull, not push.** Native notification banners are transient — they appear, you miss them,
they're gone with no trace. This widget replaces that with a persistent ambient signal you
check on your own schedule, plus a brief automatic "peek" for genuinely new attention events
so you're not required to hover to notice. The blink itself is the notification; it doesn't
expire.

---

## 2. Three surface states

### 2.1 Compact pill — default state, always present, works with or without the MPK

A slim capsule fused to the bottom of the notch, extending its silhouette. Contains **8 small
dots, one row, one per slot** — a direct 1:1 mirror of the 8 physical pads. Nothing else in
this state: no text, no icons, no labels. If you can't tell what's happening from 8 colored
dots at a glance, the color system has failed, not the layout.

- Query the actual notch bounding box at runtime (`NSScreen` safe-area insets) rather than
  hardcoding — the pill's width should match the physical notch's on-screen width so it reads
  as one continuous shape, not an appendage.
- Dot diameter ~6px, gap ~5px between dots. Capsule height just enough to contain them with
  minimal vertical padding — this should feel tight, not padded.
- Fully opaque, matched to the notch's black, not translucent. Translucency belongs to the
  expanded state, where the widget is clearly a floating panel; the pill should not look like
  a floating panel.

### 2.2 Peek — automatic, on state change; also on hover

When a slot enters an **actionable** state (permission or question), the pill briefly grows
downward to show one line: which slot, one short phrase (repo name + 2–4 word status), nothing
more. This is the notification replacement — it appears on its own, the way a banner would,
but instead of vanishing forever it settles back into a dot that's still blinking. Hovering the
pill at any time re-triggers the same peek manually, for slots that are still waiting.

- Peek auto-collapses after a few seconds back to the pill; the underlying dot keeps blinking.
- Only actionable-state transitions trigger an automatic peek. `done` does not force one — a
  green dot is enough; forcing a peek for every non-actionable transition would turn the one
  interrupt-worthy signal (something needs you) into background noise.

### 2.3 Expanded — click to open

The full session list, still governed by density-first rules — this should not look like a
standard roomy macOS dropdown. Tighter row height than the OS default, one line per session
(state dot + slot number + repo + current detail, all on one row, not stacked across two
lines), monospace throughout so columns align. A session in an actionable state gets an inline
decision affordance directly in its row (accept/deny for permissions; a "go to window" action
for questions) — the point is resolving things without a second click into a different panel.
This is allowed to use standard macOS vibrancy/blur, unlike the pill — once expanded, it's
openly a floating panel, and the notch illusion is intentionally broken.

---

## 3. Connected vs. disconnected

The widget is a **complete, standalone interface** — every state, every color, every
interaction works identically with the MPK unplugged. The hardware is additive, not required.
The only thing that should change when the MPK connects is a small, deliberately minor
connection indicator (its own muted dot or glyph, positioned apart from the 8 session dots —
don't let it compete with them for attention). Everything else — palette, motion, layout —
stays exactly the same whether or not the deck is on the desk.

---

## 4. Canonical color system

All hex values below are the single source of truth — the same values used on the physical
pads and everywhere else in the product. Don't introduce new colors per-surface.

| State | Color | Hex | Motion | Rule |
|---|---|---|---|---|
| `idle` | Slate gray | `#4A515C` | Solid | Informational |
| `thinking` | Blue | `#4F8CFF` | Solid (optional slow breathe, see §5) | Informational |
| `running_tool` | Amber | `#FFB020` | Solid | Informational |
| `waiting_permission` | Orange | `#FF9F0A` | **Fast blink** | **Actionable** |
| `waiting_question` | Violet | `#BF7BFF` | **Slow blink** | **Actionable** |
| `done` | Green | `#32D74B` | Solid, then fades to `idle` after a few seconds | Informational |
| `error` | Red | `#FF453A` | Solid | Informational — not actionable from here, don't blink it |

Note `error` is deliberately solid, not blinking: you can't fix a code error by pressing a
pad, so blinking it would violate the actionable-means-blink rule and teach the wrong reflex.
Red is reserved exclusively for error now that permission uses orange — no state shares a hue
with another.

**Background:** near-black, `#050506` to `#0A0A0B`, opaque in the pill, allowed standard
vibrancy in the expanded panel. Every state color above was chosen for contrast against this
specific background — check contrast again if the background ever changes.

**Chrome / non-semantic accents:** focus outlines, dividers, and structural UI use neutral
white/gray at reduced opacity (e.g. a plain white outline for "this is the focused slot") —
never reuse a state color for structure, or it stops meaning what it's supposed to mean.

---

## 5. Motion language

- **Fast blink** (`waiting_permission`): ~500ms full cycle. Urgent, binary, resolve-now cadence.
- **Slow blink** (`waiting_question`): ~1400ms full cycle. Roughly 3× slower than the fast
  blink — the difference must read as categorically different at a glance, not as "a little
  slower." This is the only thing distinguishing the two actionable states from across a room,
  so the gap needs to be generous.
- **Thinking breathe** (optional): a subtle opacity oscillation, ~60%–100%, slow (~2.4s cycle)
  — communicates "alive and working" without being distracting. This is the one exception to
  "solid states don't move"; keep it low-amplitude enough that it reads as a heartbeat, not a
  blink.
- **All other informational states are fully static.** No idle shimmer, no hover pulses, no
  decorative motion anywhere. Motion is a scarce resource in this design — spend it only on
  the two actionable states (plus the optional thinking-breathe), or it stops drawing the eye
  when it matters.
- **Peek transition:** quick, mechanical expand/collapse (~150–200ms), not bouncy or playful —
  this is an instrument, not a toy.

---

## 6. Typography & density rules

- Monospace everywhere data appears (repo names, states, detail text) — not just for numbers.
  Monospace is what makes tight columns align at small sizes, and it reinforces the
  instrument-panel register rather than a friendly-app register.
- No redundant labels in the compact states. A gray dot doesn't need the word "idle" next to
  it — if it needs a label to be understood, the color/motion pairing isn't doing its job.
- In the expanded list, prefer one dense line per session over two stacked lines. Only break
  onto a second line for the inline decision affordance on an actionable session — never for
  a session that's just sitting there informationally.
- No card shadows, no gradients, no big rounded corners borrowed from stock macOS widget
  styling. Flat fills, small radii, tight spacing throughout.

---

## 7. Redundant encoding (don't rely on color alone)

Every actionable state must be distinguishable without color, for colorblind-safe use and for
robustness generally:

- Permission vs. question are already redundantly encoded by **blink speed**, not just hue
  (fast vs. slow) — keep that gap large enough to be felt, not just seen.
- Position is stable and consistent: slot 3 is always the third dot, left to right, in every
  surface (pill, peek, expanded, and the physical pads) — never reorder by state or recency.
- If a future state needs adding, give it a distinct motion signature before reaching for a
  new hue — the motion vocabulary (solid / fast blink / slow blink / breathe) has more
  headroom left than the color vocabulary does.

---

## 8. Explicit anti-patterns — don't do these

- Don't animate anything in an informational state beyond the optional thinking-breathe.
- Don't use translucency/blur on the compact pill — it must look fused to the physical notch.
- Don't add icons, emoji, or text labels to the compact 8-dot state.
- Don't let the expanded view adopt standard macOS dropdown row heights/padding — it should
  feel noticeably denser than a normal app, on purpose.
- Don't reuse a semantic state color for chrome, focus rings, or dividers.
- Don't blink `error` or `done` — blinking is reserved for the two states you can resolve from
  here.
- Don't let a native OS notification banner be the only signal for an actionable state — the
  peek + persistent blink is the notification now; a banner, if used at all, is a
  supplementary ping, not the primary channel.

---

## 9. Hardware cross-reference (for consistency, not a spec to re-derive)

The physical pads set the precedent this widget mirrors: steady brightness levels live on
MIDI channels 0–3, blinking lives on channels 7–15 with channel 7 fastest. Software isn't
bound to those exact channel timings, but the *relationship* — a small number of steady levels
for informational states, a distinctly-faster blink reserved for the most urgent actionable
state — is the same shape on both surfaces. That shared shape is what makes glancing at the
deck and glancing at the notch feel like the same interface instead of two.
