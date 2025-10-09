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
        tok = tok.strip().strip('\'"')
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


def note_matches_placeholder(note, wanted):
    t = note_pitch_tuple(note)
    return (t in wanted) if t else False


def select_hidden_playback_notes(root, playback_voice=None):
    """
    Hidden playback voice selection priority:
      1) notes with print-object="no"
      2) given playback_voice number
      3) if exactly two voices present, the higher-numbered one
    """
    hidden = []
    by_voice = {}
    for note in root.findall(".//note"):
        if note.get("print-object") == "no":
            hidden.append(note)
        else:
            v = note.findtext("voice")
            if v:
                by_voice.setdefault(v.strip(), []).append(note)

    if hidden:
        return hidden
    if playback_voice is not None and str(playback_voice) in by_voice:
        return by_voice[str(playback_voice)]
    if len(by_voice) == 2:
        vnum = sorted(by_voice.keys(), key=lambda x: int(x))[-1]
        return by_voice[vnum]
    return []


def _force_natural(note):
    """Ensure note plays natural (alter=0) and remove accidental glyphs."""
    p = note.find("pitch")
    if p is None:
        return
    alt_el = p.find("alter")
    if alt_el is None:
        alt_el = ET.SubElement(p, "alter")
    alt_el.text = "0"
    for acc in list(note.findall("accidental")):
        note.remove(acc)


def flip_to_single_voice(root, keep_notes):
    """Keep only hidden voice notes, make them visible, normalize to voice 1."""
    keep_ids = set(map(id, keep_notes))
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                if id(note) in keep_ids:
                    if note.get("print-object") == "no":
                        del note.attrib["print-object"]
                    v = note.find("voice")
                    if v is not None:
                        v.text = "1"
                else:
                    meas.remove(note)


def main():
    ap = argparse.ArgumentParser(
        description="Randomize accidentals on hidden playback voice; optional single-voice flip."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--accidentals", default="sharp,flat,natural",
                    help="Comma list from {sharp,flat,natural}")
    ap.add_argument("--placeholders", default="E4,E5",
                    help="Comma list like E4,E5 (only these pitches are randomized)")
    ap.add_argument("--playback-voice", type=int, default=None,
                    help="Fallback voice number if no notes have print-object='no'")
    ap.add_argument("--flip-to-single-voice", action="store_true",
                    help="Keep only hidden playback voice and make it visible (Übungsblatt)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Allowed <alter> values from accidental keywords
    acc_choices = []
    for a in args.accidentals.split(','):
        a = a.strip().lower()
        if a == "sharp":
            acc_choices.append(1)
        elif a == "flat":
            acc_choices.append(-1)
        elif a == "natural":
            acc_choices.append(0)
    if not acc_choices:
        acc_choices = [0]

    wanted = parse_placeholders(args.placeholders)

    tree = ET.parse(args.input)
    root = tree.getroot()

    hidden_notes = select_hidden_playback_notes(root, playback_voice=args.playback_voice)

    # 1) Endpoints safety in hidden voice: first E4 and last E5 -> natural, never altered
    indices_to_skip = set()
    first_e4 = None
    last_e5 = None
    for idx, n in enumerate(hidden_notes):
        t = note_pitch_tuple(n)
        if t == ("E", 4) and first_e4 is None:
            first_e4 = idx
        if t == ("E", 5):
            last_e5 = idx
    if first_e4 is not None:
        _force_natural(hidden_notes[first_e4])
        indices_to_skip.add(first_e4)
    if last_e5 is not None:
        _force_natural(hidden_notes[last_e5])
        indices_to_skip.add(last_e5)

    # 2) Randomize accidentals on OTHER hidden notes that match placeholders
    changed = 0
    for idx, note in enumerate(hidden_notes):
        if idx in indices_to_skip:
            continue
        if not note_matches_placeholder(note, wanted):
            continue
        p = note.find("pitch")
        if p is None:
            continue
        alter = random.choice(acc_choices)
        alt_el = p.find("alter")
        if alt_el is None:
            alt_el = ET.SubElement(p, "alter")
        alt_el.text = "0" if alter == 0 else str(int(alter))
        # hidden voice prints nothing anyway; remove any explicit accidental glyphs
        for acc in list(note.findall("accidental")):
            note.remove(acc)
        changed += 1

    # 3) Flip to single visible voice (solution sheet)
    if args.flip_to_single_voice and hidden_notes:
        flip_to_single_voice(root, hidden_notes)

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} hidden-voice notes. "
          f"Flipped: {bool(args.flip_to_single_voice)}. "
          f"Wrote {args.output}")


if __name__ == "__main__":
    main()
