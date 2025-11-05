# Übungsblatt Generator Toolkit

A small toolkit to build ear‑training worksheets (`Übungsblatt`) and student versions (`Arbeitsblatt`) from MusicXML templates. It produces four sections:

- **Scales** (`Hoeren_scales.musicxml`)
- **Intervals** (`Hoeren_intervals.musicxml`)
- **Chords** (`Hoeren_chords.musicxml`)
- **Rhythm** (`Hoeren_rhythm.musicxml`)

The toolkit is **profile‑able** via YAML, deterministic with a seed, and generates **Arbeitsblatt** variants automatically (including a special pipeline for scales).

---

## Quick Start

1) Put your templates in `sibelius/` (or any folder you like) and point the YAML to them:

```
sibelius/Hoeren_scales.musicxml
sibelius/Hoeren_intervals.musicxml
sibelius/Hoeren_chords.musicxml
sibelius/Hoeren_rhythm.musicxml
```

2) Edit `uebungsblatt.yaml` (see schema below).

3) Generate everything:

```bash
python uebungsblatt_cli.py --config uebungsblatt.yaml
```

This will create:

```
OUT/
  Hoeren_scales.musicxml
  Hoeren_scales_arbeitsblatt.musicxml
  Hoeren_intervals.musicxml
  Hoeren_intervals_arbeitsblatt.musicxml
  Hoeren_chords.musicxml
  Hoeren_chords_arbeitsblatt.musicxml
  Hoeren_rhythm.musicxml
  Hoeren_rhythm_arbeitsblatt.musicxml
```

---

## Requirements

- Python 3.9+
- `PyYAML` (for the CLI): `pip install pyyaml`
- A notation app that supports MusicXML (MuseScore, Dorico, Finale, Sibelius, …). Toolkit decisions were tested to be **MuseScore‑friendly** (e.g., using `print-object="no"` and `<forward>` where needed).

---

## Repository Layout (expected)

```
.
├─ uebungsblatt_cli.py           # Main orchestrator
├─ generate_scales.py            # Scales generator (single voice)
├─ generate_intervals.py         # Intervals generator
├─ generate_chords.py            # Chords generator
├─ generate_rhythms.py           # Rhythms generator
├─ make_arbeitsblatt.py          # Post‑processor to create worksheets
├─ uebungsblatt.yaml             # Config + (optional) profiles
└─ sibelius/
   ├─ Hoeren_scales.musicxml
   ├─ Hoeren_intervals.musicxml
   ├─ Hoeren_chords.musicxml
   └─ Hoeren_rhythm.musicxml
```

> You can rename/move templates; just update `inputs:` in the YAML.

---

## YAML Configuration (schema & example)

```yaml
outdir: OUT            # Where to write all outputs
seed: 42               # Global RNG seed (determinism across runs)
what: all              # (optional) not used by current CLI; reserved

inputs:
  scales: sibelius/Hoeren_scales.musicxml
  intervals: sibelius/Hoeren_intervals.musicxml
  chords: sibelius/Hoeren_chords.musicxml
  rhythms: sibelius/Hoeren_rhythm.musicxml

# --- Section knobs ---

scales:
  placeholders: [E4, E5]         # Pitches eligible for randomization (letter+octave)
  accidentals: [sharp, flat, natural]  # Allowed set for randomization

intervals:
  set: [m2, M2, m3, M3, P4, TT, P5, m6, M6, m7, M7, P8]
  direction: both                # up | down | both

chords:
  triads: [maj, min, dim]        # subset of maj/min/dim/aug
  inversion: random              # root | first | second | random

rhythms:
  note_prob: 0.7                 # (if used by your local generator)

# --- Worksheet behavior (Arbeitsblatt) ---

worksheet:
  scales: hide                   # hide | delete  (scales uses `hide`: make accidentals invisible)
  intervals: hide                # hide quarters or delete quarters
  chords: hide                   # hide or delete upper staff (or <chord/> fallback)
  rhythms: hide                  # produce a blank page (see details below)

# Optional profiles to override any subset of the above
profiles:
  easy:
    seed: 11
    scales:
      accidentals: [natural]
    intervals:
      set: [M2, m3, P4, P5]
      direction: up

  exam:
    seed: 99
    scales:
      placeholders: [E4, E5]
      accidentals: [sharp, flat, natural]
    intervals:
      set: [m2, M2, m3, M3, P4, TT, P5, m6, M6, m7, M7, P8]
      direction: both
```

Use a profile:

```bash
python uebungsblatt_cli.py --config uebungsblatt.yaml --profile exam
```

---

## CLI (`uebungsblatt_cli.py`)

The CLI reads the YAML, calls each generator, and then calls `make_arbeitsblatt.py` to produce the corresponding worksheet. It also **auto‑creates the scales Arbeitsblatt from the Übungsblatt** using the “hide accidentals” rule.

**Command:**

```bash
python uebungsblatt_cli.py --config uebungsblatt.yaml [--profile NAME]
```

### What the CLI does per section

- **Scales**
  
  1. `generate_scales.py` → `OUT/Hoeren_scales.musicxml`
     - Single‑voice input & output.
     - Randomizes accidentals for configured placeholders.
     - **First E4** and **last E5** are **forced natural** and **excluded** from randomization.
  2. `make_arbeitsblatt.py --mode scales --action hide`
     - Takes the Übungsblatt output as input.
     - Makes **all accidentals invisible** (and inserts invisible accidentals if only `<alter>` is present).

- **Intervals**
  
  - `generate_intervals.py` → Übungsblatt
  - `make_arbeitsblatt.py --mode intervals` → hide/delete quarters (configurable)

- **Chords**
  
  - `generate_chords.py` → Übungsblatt
  - `make_arbeitsblatt.py --mode chords` → hide/delete upper staff (fallback: `<chord/>` tones)

- **Rhythm**
  
  - `generate_rhythms.py` → Übungsblatt
  - `make_arbeitsblatt.py --mode rhythms`
    - **Hide:** produces a **blank** page per measure by replacing notes with `<forward>` and removing `<backup>` to avoid timing corruption.
    - **Delete:** converts pitched notes to rests (keeps timing).

---

## Generators — Flags

### `generate_scales.py` (single voice)

```
--input PATH                # MusicXML template
--output PATH               # output file
--accidentals LIST          # e.g. 'sharp,flat,natural'
--placeholders LIST         # e.g. 'E4,E5' (only these pitches randomized)
--seed INT                  # RNG seed for determinism
```

**Behavior**

- Only pitches listed in `--placeholders` are randomized.
- Endpoint safety: the **first E4** and **last E5** in the score are **forced natural** and excluded from randomization.
- Any existing `<accidental>` elements on changed notes are removed (MuseScore renders based on `<alter>`; the Arbeitsblatt step will take care of visibility).

### `generate_intervals.py`, `generate_chords.py`, `generate_rhythms.py`

Your local versions may expose slightly different flags; the CLI passes:

- `--input`, `--output`, `--seed`
- Intervals: set & direction from YAML
- Chords: triad set & inversion from YAML
- Rhythms: any parameters supported by your generator (e.g., `note_prob`).

---

## Worksheet Creator — `make_arbeitsblatt.py`

```
--mode {scales,intervals,chords,rhythms}
--action {hide,delete}
--input PATH
--output PATH
```

### Modes

- **scales / hide**  
  
  - Keep playback exactly as in Übungsblatt.
  - Make **all accidentals invisible** by setting `print-object="no"` on `<accidental>`.
  - If a note has `<alter>` but no `<accidental>`, add an `<accidental print-object="no">…</accidental>` so **nothing prints**.

- **intervals / hide**  
  
  - Hide quarter notes (`print-object="no"`); whole notes remain as prompts.

- **intervals / delete**  
  
  - Remove quarter notes entirely.

- **chords / hide**  
  
  - Hide upper staff (`<staff>1</staff>`). Fallback: hide notes with `<chord/>` (upper chord tones).

- **chords / delete**  
  
  - Delete upper staff. Fallback: delete `<chord/>` notes.

- **rhythms / hide**  
  
  - **Blank page output:** remove all `<backup>`; replace each `<note>` with a `<forward>` of equal duration. Avoids timing corruption and draws nothing.

- **rhythms / delete**  
  
  - Convert pitched notes to rests; remove beams/flags/stems/notations to reduce clutter.

---

## Determinism & Reproducibility

- Set a top‑level `seed:` in YAML (or pass per generator).  
- Reusing the same **seed + template** yields the same Übungsblatt & Arbeitsblatt pairing.

---

## Common Recipes

### Re‑roll only scales with a different seed

```bash
python generate_scales.py --input sibelius/Hoeren_scales.musicxml \
  --output OUT/Hoeren_scales.musicxml \
  --accidentals sharp,flat,natural \
  --placeholders E4,E5 \
  --seed 123

python make_arbeitsblatt.py --mode scales --action hide \
  --input OUT/Hoeren_scales.musicxml \
  --output OUT/Hoeren_scales_arbeitsblatt.musicxml
```

### Use the `exam` profile

```bash
python uebungsblatt_cli.py --config uebungsblatt.yaml --profile exam
```

---

## Troubleshooting

- **Rhythm Arbeitsblatt shows “weird” spacing or corrupt measure warnings**  
  Ensure you’re on the latest `make_arbeitsblatt.py`. The `rhythms_hide` step now removes **all `<backup>`** and replaces **every `<note>` with `<forward>`** to keep timing consistent with “no drawing.”

- **Accidentals still appear on Scales Arbeitsblatt**  
  Some notes may only have `<alter>` without `<accidental>`; the script inserts **invisible** accidentals in this case. Verify your notation app honors `print-object="no"` for `<accidental>` (MuseScore does).

- **Chords upper staff didn’t hide**  
  If your template lacks `<staff>` numbers, the fallback hides notes with `<chord/>` (upper chord tones). If your voicing uses another pattern, share a sample and we can add a custom rule.

---

## Notes for MuseScore

- MuseScore renders accidentals from `<pitch><alter>` and from explicit `<accidental>` elements. Making `<accidental>` invisible (`print-object="no"`) **suppresses the glyph** while **keeping playback**.
- `<forward>` advances time without drawing. Replacing notes/rests with `<forward>` yields **blank measures** that remain valid MusicXML.

---

## License

Do whatever works for your classroom. If you publish, a mention is appreciated. 🎵

## 

Install locally:

```bash
# create venv (only the first time)
python3 -m venv ./.venv

# actrivate
source .venv/bin/activate
```

## Prep & wrap

You still need to do, after generating musicxml files:

- Open with Musescore
- In musescore, set invisible objects to remain hidden
- for the rhythm, select all notes/rests and make invisible
- for the scales, select all alteration symbols and make invisible
- Save as musescore files
- (optional) bundle in a .zip for sharing
