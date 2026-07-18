# Protocol discovery notes

Status: **transport CCs, pad notes, and encoder CCs live-verified on the actual unit
with `tools/mapping_ui.py` (see "Live verification session" below) — this is now
ground truth and supersedes the third-party docs in several places. Pad-LED-color
scheme has a strong lead but is unverified on real hardware. Screen text protocol
unresolved — treat as stretch goal per CLAUDE.md §8 step 5.**

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

## Unverified lead: pad LED color is Note-On based, not SysEx

`MPK_mini_IV/colors.py` (decompiled) shows pad LED colors are set via a plain **Note
On** message, not SysEx:

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

i.e. `note_on(status=0x90 + channel_offset, note=<pad's note number>, velocity=<color
index>)`. The four named channel offsets (`HALF_BRIGHTNESS_LED_CHANNEL`,
`FULL_BRIGHTNESS_LED_CHANNEL`, `BLINK_LED_CHANNEL`, `PULSE_LED_CHANNEL`) come from a
per-device `midi.py` that Ableton's decompile dump is missing for `MPK_mini_IV`
specifically (present for other devices, not this one — likely an extraction gap in
the `gluon` mirror, not something we can fix by reading harder).

`APC64/midi.py` (same framework generation, different device) has the same four
constant *names* with values `HALF=0, FULL=6, PULSE=10, BLINK=14` — plausible as a
starting guess (looks like `base_channel + N*4`), but **APC64 is not the same
hardware and this is a guess, not a confirmed value.** Do not hardcode it as fact.

This is genuinely good news for the v1 scope: if confirmed, pad LEDs need **no SysEx
at all** — just a Note On, which is simple, low-risk to test (unlike blind SysEx
function-code guessing — see the firmware-update-mode warning above), and squarely
within what `mido` already does.

### Recommended next verification step (Day 2, needs the physical unit)

1. Open the MIDI *output* port (`MPK mini IV MIDI Port` or `...DAW Port`) alongside
   `tools/midi_monitor.py` listening on the corresponding input, or just watch the pad
   with your eyes.
2. Send `note_on(channel=0, note=48, velocity=5)` (guessing "channel offset 0 = full
   brightness, red") to pad 1's note. Observe: does the pad light up? What color?
3. Sweep small channel values (0-3) with a known velocity (e.g. 5 = red per the table
   above) to find which channel value actually lights the pad steady-on vs. does
   nothing vs. errors.
4. Once one channel value is confirmed to produce a static color, test another small
   channel value against the same note to look for blink/pulse behavvior (needed for
   `waiting_permission`'s blink requirement, §6).
5. Write confirmed values into `daemon/protocol/pad_colors.py`, replacing the
   `UNVERIFIED` placeholders and the module-level warning docstring.

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
