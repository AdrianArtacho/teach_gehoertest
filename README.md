# Tonmeisterstudium

Here are materials and links to prepare the access exam to the Tonmeisterstudium at the mdw.

---

## Usage

### 1. Teil: Hören und Notieren

--- 

## Run locally

```bash
# create venv (only the first time)
python3 -m venv ./.venv

# actrivate
source .venv/bin/activate
```

```bash
# 1) Scales: randomize accidentals of E4 / E5 placeholders in the “Tonleiter” section
python generate_scales.py --input sibelius/Hoeren_1.musicxml --output out_scales.musicxml --accidentals sharp,flat,natural --seed 42

# 2) Intervals: set the 2nd note at a chosen interval from the 1st
python generate_intervals.py --input sibelius/Hoeren_1.musicxml --output out_intervals.musicxml --intervals m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8 --direction both --seed 1

# 3) Chords: turn single notes into stacked triads (maj/min/dim/aug) with optional inversion
python generate_chords.py --input sibelius/Hoeren_1.musicxml --output out_chords.musicxml --triads maj,min,dim --inversion random --section-keyword Dreiklang --seed 7

# 4) Rhythms: randomize note/rest pattern while preserving durations
python generate_rhythms.py --input sibelius/Hoeren_1.musicxml --output out_rhythms.musicxml --note-prob 0.65 --seed 99
```
