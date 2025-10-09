#!/usr/bin/env python3
import argparse
import random
import re
import xml.etree.ElementTree as ET


def parse_placeholders(s: str):
    """
    Accepts a comma list like: E4,E5  or  ["E4","E5"]
    Returns a set of (STEP, OCTAVE) tuples, e.g. {("E",4), ("E",5)}
    """
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
    """Return (STEP, OCTAVE) or None if not a pitched note."""
    p = note.find("pitch")
    if p is None:
        return None
    step = (p.findtext("step") or "").upper()
    octv = p.findtext("octave")
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
    Pick the notes that belong to the hidden playback voice.

    Priority:
      1) Any note with print-object="no".
      2) Fallback: notes with voice == playback_voice (if provided).
      3) Fallback: if exactly two voices exist, pick the higher-numbered one.
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

    if playback_voice is not None:
        key = str(playback_voice)
        if key in by_voice:
            return by_voice[key]

    if len(by_voice) == 2:
        # choose the higher-numbered voice as "hidden"
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
    """
    Keep only the notes present in keep_notes (the hidden voice),
    make them visible, and normalize to voice 1.
    """
    keep_ids = set(map(id, keep_notes))

    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                if id(note) in keep_ids:
                    # unhide if needed
                    if note.get("print-object") == "no":
                        del note.attrib["print-object"]
                    # normalize to voice 1 (clean)
                    v = note.find("voice")
                    if v is not None:
                        v.text = "1"
                else:
                    meas.remove(note)


def main():
    ap = argparse.ArgumentParser(
        description="Randomize accidentals on the hidden playback voice only "
                    "and (optionally) flip to a single visible voice."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)

    # Which accidentals are allowed
    ap.add_argument(
        "--accidentals",
        default="sharp,flat,natural",
        help="Comma list from {sharp,flat,natural}"
    )

    # Which pitch placeholders to consider (letter+octave). Defaults to E4,E5.
    ap.add_argument(
        "--placeholders",
        default="E4,E5",
        help="Comma list (e.g. E4,E5), only these pitches get randomized (endpoints are guarded)"
    )

    # Hidden voice fallback if no print-object='no' found
    ap.add_argument(
        "--playback-voice",
        type=int,
        default=None,
        help="Fallback voice number (e.g. 2) to treat as hidden if notes aren't marked print-object='no'"
    )

    # Flip to a single visible voice (solution sheet)
    ap.add_argument(
        "--flip-to-single-voice",
        action="store_true",
        help="Keep only the hidden playback voice and make it visible (for the Übungsblatt)"
    )

    ap.add_argument("--seed", type=int, default=None)

    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    # Allowed accidental choices -> <alter> values
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

    # Identify the first E4 and the last E5 in the hidden voice
    indices_to_skip = set()
    first_e4 = None
    last_e5 = None
    for idx, n in enumerate(hidden_notes):
        t = note_pitch_tuple(n)
        if t == ("E", 4) and first_e4 is None:
            first_e4 = idx
        if t == ("E", 5):
            last_e5 = idx

    # Force endpoints to natural (never altered)
    if first_e4 is not None:
        _force_natural(hidden_notes[first_e4])
        indices_to_skip.add(first_e4)
    if last_e5 is not None:
        _force_natural(hidden_notes[last_e5])
        indices_to_skip.add(last_e5)

    # Randomize ONLY other hidden-voice notes that match placeholders
    changed = 0
    for idx, note in enumerate(hidden_notes):
        if idx in indices_to_skip:
            continue  # endpoints locked to natural

        if not note_matches_placeholder(note, wanted):
            continue

        p = note.find("pitch")
        if p is None:
            continue

        alter = random.choice(acc_choices)
        alt_el = p.find("alter")
        if alter == 0:
            if alt_el is None:
                alt_el = ET.SubElement(p, "alter")
            alt_el.text = "0"
        else:
            if alt_el is None:
                alt_el = ET.SubElement(p, "alter")
            alt_el.text = str(int(alter))

        # hidden voice prints nothing anyway; remove any explicit accidental glyphs
        for acc in list(note.findall("accidental")):
            note.remove(acc)

        changed += 1

    # Flip (solution sheet): keep only hidden voice and make it visible
    if args.flip_to_single_voice and hidden_notes:
        flip_to_single_voice(root, hidden_notes)

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} hidden-voice notes. Flipped: {bool(args.flip_to_single_voice)}. Wrote {args.output}")


if __name__ == "__main__":
    main()
