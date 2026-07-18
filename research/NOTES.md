# Protocol discovery notes

Status: **transport CCs, pad notes, encoder CCs, and pad LED colors are all
live-verified on the actual unit** (`tools/mapping_ui.py` for input mapping,
`tools/pad_color_lab.py` for LED output) — this is ground truth, superseding the
third-party docs in several places. Only the onboard screen text protocol remains
unresolved — treated as a stretch goal per CLAUDE.md §8 step 5.

## Sources used

1. `github.com/gluon/AbletonLive12_MIDIRemoteScripts` — official Ableton Live 12
   control-surface scripts, decompiled (pycdc/uncompyle6, "may be partial"). Contains
   `MPK_mini_IV/__init__.py`, `colors.py`, `display_status.py`. Copied locally into
   `research/akai_script_dump/MPK_mini_IV/` for reference. Also pulled `APC64/midi.py`
   as a same-generation comparison (`research/akai_script_dump/APC64_reference/`) —
   APC64 is a different device but shares the same `ableton.v3.control_surface`
   framework generation, so its constant *names* (not values) are a useful hint.
2. `github.com/philoSurfer/reason_akai_mpk_mini_mk4` — independent, non-Ableton
   reverse-engineering project (Reason Studios Remote integration) with its own
   `docs/MPK_MINI_IV_MIDI_SPEC.md`, built from live device probing. Primary source
   for the device-ID/SysEx-preset findings below. It also independently reported the
   same transport CC numbers as CLAUDE.md §7's community source — **but live testing
   on this actual unit (below) found three of those CCs, and the pad note numbers,
   to be wrong.** Docs from other people's units are a starting hypothesis, not a
   substitute for testing your own hardware — don't skip that step next time either.
3. **Live capture on this unit** via `tools/mapping_ui.py`, a self-service local web
   page that streams every incoming MIDI message in real time so you can press a
   control and immediately see what it sends, no guessing which physical button is
   which from a doc. Raw output saved to `research/live_mapping.json`.

## Confirmed: device identity

- Manufacturer ID `0x47` (71, AKAI), device family `0x5D` (93), device member `0x19` (25).
- Matches `get_capabilities()` in the Ableton script exactly
  (`controller_id(vendor_id=2536, product_ids=[93], model_name=['MPK mini IV'])` —
  vendor_id 2536 = USB VID, distinct from the MIDI SysEx manufacturer ID 0x47).
- 5 MIDI ports exposed: `MPK mini IV MIDI Port`, `DAW Port`, `Plugin Port`, `Software
  Control Port`, plus a DIN-out-only port. Confirmed present on this machine via
  `mido.get_input_names()`.

## Live verification session (ground truth for this unit, preset 1 / DAW)

Captured with `tools/mapping_ui.py` against the real device on preset 1. Full raw
JSON in `research/live_mapping.json`. This is what `daemon/config.py` now encodes.

### Transport CCs — corrected in 3 places vs. the docs

| Button | CC | vs. docs |
|---|---|---|
| Play/Stop | 76 | matches |
| Record | 77 | matches |
| Loop | 74 | matches |
| Undo | 73 | matches, SHIFT+Undo = Redo |
| Tap Tempo | **82** | docs said 11 — **wrong for this unit** |
| Shift | 17 | matches, momentary: 127 press / 0 release |
| Bank − | **80** | docs said 15 — **wrong for this unit** |
| Bank + | **81** | docs said 16 — **wrong for this unit** |
| Fast Forward | *(none)* | **this unit has no dedicated FF button** — docs said CC78 |

All sent on channel 1. Observed exclusively on the **DAW Port**, not the plain MIDI
Port (docs claimed both — didn't hold up here). Toggle buttons (Play/Stop, Record,
Loop, Undo) send 127 on press only, no release message. Momentary buttons (Tap
Tempo, Shift, Bank −/+) send 127 on press, 0 on release.

### Pad notes — corrected, contiguous instead of the docs' non-contiguous mapping

Pads 1-8 send Note On/Off on **channel 10** (0-indexed channel 9), notes **36-43**
sequentially — not the non-contiguous 48/50/52/53/55/57/59/60 the docs listed.
Interestingly closer to the General MIDI drum note range (36 = kick) than to the
"DAW preset" table the Reason project documented for their own unit. Seen on both
the MIDI Port and the DAW Port (inconsistently — don't rely on only one).

**This supersedes `daemon/config.py`'s previous `PAD_NOTES =
[48, 50, 52, 53, 55, 57, 59, 60]`** (itself already a correction of an earlier
placeholder) — now `[36, 37, 38, 39, 40, 41, 42, 43]`.

### Push-encoder — no prior documentation existed for this at all

| Control | CC | Notes |
|---|---|---|
| Turn | 14 | relative: value 1 = one step clockwise, value 127 = one step counter-clockwise |
| Press | 13 | momentary, 127 on press |

## Confirmed: SysEx envelope + preset read/write (not directly needed for AgentDeck, but validates the device-ID bytes above)

```
F0 47 [channel] 5D [function] [len_hi] [len_lo] [data...] F7
```
Function `0x66` = get-preset request, `0x67` = preset-data response. Presets are read
over the "Software Control Port". AgentDeck doesn't need to read/write presets, but
this confirms the SysEx envelope shape in case screen/LED protocol turns out to be
SysEx-based too.

**Warning from the Reason project's own notes, worth heeding**: *"Sending certain
SysEx function codes can trigger firmware update mode. Avoid sending untested function
codes in bulk."* — don't brute-force unknown function codes against the real unit.

## Live-verified: pad LED color is Note-On based, not SysEx

`MPK_mini_IV/colors.py` (decompiled) hypothesized pad LED colors are set via a plain
**Note On** message, not SysEx — this is now **confirmed live on the real unit**:

```python
class UIButtonColor(SimpleColor):
    def draw(self, interface):
        interface.send_midi((NOTE_ON_STATUS + self._channel, interface.message_identifier(), self._value))

class Rgb:
    OFF = ...      # value 0
    GREY = ...     # value 1
    WHITE = ...    # value 3
    RED = ...      # value 5
    AMBER = ...    # value 9
    GREEN = ...    # value 21
    BLUE = ...     # value 45
```

i.e. `note_on(status=0x90 + channel, note=<pad's note number>, velocity=<color
index>)`. Confirmed with `tools/pad_color_lab.py` (a local web page, same
press-and-see-immediately pattern as `tools/mapping_ui.py`, purpose-built for this
since LED state can't be read back over MIDI — the user has to look at the pad and
report what they see).

**Critical detail that cost the most debugging time**: these Note On messages only
take effect on the **DAW Port** — identical to the transport-CC finding above. The
first round of testing sent everything on the plain MIDI Port and saw zero effect at
all, which looked like the whole hypothesis was wrong. Always try the DAW Port first
for anything LED/feedback-related on this device.

### Confirmed channel semantics (0-indexed MIDI channel byte)

| Channel(s) | Behavior |
|---|---|
| 0-3 | steady, brightness increases with channel number (0=dim, 3=bright) |
| 6 | also steady (not investigated further — 0-3 already cover steady use cases) |
| 7-15 | blinking; blink interval gets **longer** as channel number increases (7=fastest, 15=slowest) |

Color (velocity) values were already correct from the decompiled script and are now
confirmed live — every color renders as expected except GREY, which is visually too
dim to distinguish from OFF on this unit (still encoded in `pad_colors.py` for
completeness, just don't rely on it being visually distinct).

Per CLAUDE.md §6 ("Only `waiting_permission` blinks... everything else is
display-only"), only that one state uses a `BLINK_*` channel (channel 7, the fastest
blink) — every other state uses `BRIGHTNESS_DIM` (0) or `BRIGHTNESS_BRIGHT` (3).
`error` deliberately reuses RED at steady brightness rather than blink, so it stays
visually distinct from `waiting_permission`.

Implemented and live-tested end-to-end in `daemon/protocol/pad_colors.py` —
`message_for_state()` output for `waiting_permission` was sent to the real pad 1 and
confirmed to blink red as expected.

## Unresolved: onboard screen text protocol

No source found (Ableton dump, Reason repo, or general web search) documents a
free-text or fixed-field screen-write SysEx for the MPK Mini IV specifically.
`display_status.py`'s decompile is too incomplete to reconstruct anything (`class
DisplayStatusComponent(Component): pass — WARNING: Decompyle incomplete`). Per
CLAUDE.md §8 step 5 / §3, this downgrades to a stretch goal — lean on the macOS
notification banner (`rumps.notification`, already implemented in
`daemon/menubar.py`) as the primary "glance" mechanism. `daemon/protocol/screen.py`
is left as an unimplemented stub with this status recorded, not a dead end to revisit
blindly — if picked up again, the SysEx envelope confirmed above (`F0 47 ch 5D
func ...`) is at least a starting point for guessing at screen-write function codes,
but doing so risks the firmware-update-mode warning above and should be done
cautiously, one function code at a time, with the device factory-resettable.
