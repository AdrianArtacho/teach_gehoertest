
#!/usr/bin/env python3
import argparse
import random
import re
import xml.etree.ElementTree as ET

def parse_placeholders(s: str):
    """Accepts E4,E5 or ["E4","E5"]; returns {("E",4),("E",5)}."""
    result = set()
    s = (s or "").strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    for tok in s.split(','):
        tok = tok.strip().strip('\'\"')
        m = re.fullmatch(r"([A-Ga-g])(?:[#b])?(\d)", tok)
        if not m:
            continue
        result.add((m.group(1).upper(), int(m.group(2))))
    return result or {("E", 4), ("E", 5)}

def note_pitch_tuple(note):
    p = note.find("pitch")
    if p is None:
        return None
    step = (p.findtext("step") or "").upper()
    octv = note.findtext("octave")
    if not step or not octv:
        return None
    try:
        o = int(octv)
    except Exception:
        return None
    return (step, o)

def select_all_pitched_notes(root):
    notes = []
    for note in root.findall(".//note"):
        if note.find("pitch") is not None:
            notes.append(note)
    return notes

def _set_alter(note, val):
    p = note.find("pitch")
    if p is None: return
    alt_el = p.find("alter")
    if alt_el is None:
        alt_el = ET.SubElement(p, "alter")
    alt_el.text = str(int(val))

def main():
    ap = argparse.ArgumentParser(description="Randomize accidentals on a single-voice scales file.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--accidentals", default="sharp,flat,natural",
                    help="Comma list from {sharp,flat,natural}")
    ap.add_argument("--placeholders", default="E4,E5",
                    help="Comma list like E4,E5 (only these pitches are randomized)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # map input keywords to <alter> values
    acc_choices = []
    for a in args.accidentals.split(','):
        a = a.strip().lower()
        if a == "sharp": acc_choices.append(1)
        elif a == "flat": acc_choices.append(-1)
        elif a == "natural": acc_choices.append(0)
    if not acc_choices:
        acc_choices = [0]

    wanted = parse_placeholders(args.placeholders)

    tree = ET.parse(args.input); root = tree.getroot()

    # Get all pitched notes in score order
    pitched = select_all_pitched_notes(root)

    # Locate first E4 and last E5 to force natural and exclude from randomization
    first_e4_idx = None
    last_e5_idx = None
    for idx, n in enumerate(pitched):
        t = note_pitch_tuple(n)
        if t == ("E", 4) and first_e4_idx is None:
            first_e4_idx = idx
        if t == ("E", 5):
            last_e5_idx = idx

    # Force endpoints natural (if present)
    if first_e4_idx is not None:
        _set_alter(pitched[first_e4_idx], 0)
        for acc in list(pitched[first_e4_idx].findall("accidental")):
            pitched[first_e4_idx].remove(acc)
    if last_e5_idx is not None:
        _set_alter(pitched[last_e5_idx], 0)
        for acc in list(pitched[last_e5_idx].findall("accidental")):
            pitched[last_e5_idx].remove(acc)

    # Randomize the rest, but only for placeholders
    changed = 0
    for idx, note in enumerate(pitched):
        if idx == first_e4_idx or idx == last_e5_idx:
            continue
        t = note_pitch_tuple(note)
        if not t or t not in wanted:
            continue
        alter = random.choice(acc_choices)
        _set_alter(note, alter)
        # Clean any explicit accidental glyphs; engraving can infer glyphs from alter
        for acc in list(note.findall("accidental")):
            note.remove(acc)
        changed += 1

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} notes. Wrote {args.output}")

if __name__ == "__main__":
    main()
