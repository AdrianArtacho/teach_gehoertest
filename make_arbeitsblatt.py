#!/usr/bin/env python3
import argparse
import xml.etree.ElementTree as ET

def save(tree, path):
    tree.write(path, encoding="utf-8", xml_declaration=True)

def _staff_num(note):
    s = note.findtext("staff")
    return int(s) if s and s.isdigit() else None

# ---------------- Scales ----------------
def scales_hide(root):
    """
    Scales (Arbeitsblatt): keep BOTH voices exactly like template.
    Do NOT touch playback (<pitch><alter>) nor hidden voice.
    Only strip accidental *glyphs* from visible notes.
    """
    hidden = 0
    for note in root.findall(".//note"):
        if note.get("print-object") == "no":
            continue  # leave hidden playback voice unchanged
        for acc in list(note.findall("accidental")):
            note.remove(acc)
            hidden += 1
    return hidden

def scales_delete(root):
    # For scales, deleting isn't meaningful; behave same as hide.
    return scales_hide(root)

# ---------------- Intervals ----------------
def intervals_hide(root):
    """
    Hide quarter notes (solutions) by setting print-object="no";
    leaves whole notes (prompts) visible.
    """
    hidden = 0
    for note in root.findall(".//note"):
        typ = (note.findtext("type") or "").strip().lower()
        if typ == "quarter":
            note.set("print-object", "no")
            hidden += 1
    return hidden

def intervals_delete(root):
    """
    Remove quarter notes entirely.
    """
    removed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                typ = (note.findtext("type") or "").strip().lower()
                if typ == "quarter":
                    meas.remove(note)
                    removed += 1
    return removed

# ---------------- Chords ----------------
def chords_hide(root):
    """
    Hide ALL notes in the upper staff (staff == 1). Keep lower staff visible.
    Fallback if no <staff>: hide chord tones (notes carrying <chord/>).
    """
    saw_staff = False
    hidden = 0
    for note in root.findall(".//note"):
        sn = _staff_num(note)
        if sn is not None:
            saw_staff = True
            if sn == 1:
                note.set("print-object", "no")
                hidden += 1
    if not saw_staff:
        # fallback: hide chord tones above the bass (notes that have <chord/>)
        for note in root.findall(".//note"):
            if note.find("chord") is not None:
                note.set("print-object", "no")
                hidden += 1
    return hidden

def chords_delete(root):
    """
    Delete all notes in upper staff (staff == 1).
    Fallback: delete notes with <chord/>.
    """
    saw_staff = False
    removed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                sn = _staff_num(note)
                if sn is not None:
                    saw_staff = True
                    if sn == 1:
                        meas.remove(note)
                        removed += 1
    if not saw_staff:
        for part in root.findall("part"):
            for meas in part.findall("measure"):
                for note in list(meas.findall("note")):
                    if note.find("chord") is not None:
                        meas.remove(note)
                        removed += 1
    return removed

# ---------------- Rhythms ----------------
def _strip_visual_children(note):
    """
    Remove beams, flags, stems, noteheads, accidentals, dots, ties, and notations.
    Helps avoid any visual residue when hiding notes.
    """
    for tag in ["beam", "flag", "stem", "notehead", "accidental", "dot"]:
        for el in list(note.findall(tag)):
            note.remove(el)
    for el in list(note.findall("tie")):
        note.remove(el)
    notations = note.find("notations")
    if notations is not None:
        note.remove(notations)

def rhythms_hide(root):
    """
    Hide all pitched notes AND remove visible rests:
      - Pitched notes -> set print-object="no" and strip visuals (beams, stems, flags, etc.).
      - Rests -> replace note with <forward> of same duration (advances time without drawing).
    """
    changed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                if note.find("rest") is not None:
                    # Replace rest-note with <forward> of same duration
                    dur_el = note.find("duration")
                    fwd = ET.Element("forward")
                    if dur_el is not None:
                        d = ET.SubElement(fwd, "duration")
                        d.text = dur_el.text
                    idx = list(meas).index(note)
                    meas.insert(idx, fwd)
                    meas.remove(note)
                    changed += 1
                elif note.find("pitch") is not None:
                    note.set("print-object", "no")
                    _strip_visual_children(note)
                    changed += 1
    return changed

def rhythms_delete(root):
    """
    Convert all pitched notes to rests (preserve duration) and strip visuals.
    """
    changed = 0
    for note in root.findall(".//note"):
        p = note.find("pitch")
        if p is not None:
            note.remove(p)
            if note.find("rest") is None:
                ET.SubElement(note, "rest")
            _strip_visual_children(note)
            changed += 1
    return changed

# ---------------- Dispatch ----------------
def apply_mode(root, page, action):
    if page == "scales":
        return (scales_hide if action == "hide" else scales_delete)(root)
    if page == "intervals":
        return (intervals_hide if action == "hide" else intervals_delete)(root)
    if page == "chords":
        return (chords_hide if action == "hide" else chords_delete)(root)
    if page == "rhythms":
        return (rhythms_hide if action == "hide" else rhythms_delete)(root)
    raise ValueError("unknown page")

def main():
    ap = argparse.ArgumentParser(description="Create worksheet/Arbeitsblatt variants (hide or delete).")
    ap.add_argument("--mode", required=True, choices=["scales", "intervals", "chords", "rhythms"], help="Which page type")
    ap.add_argument("--action", default="hide", choices=["hide", "delete"], help="hide or delete solutions")
    ap.add_argument("--input", required=True, help="Source MusicXML")
    ap.add_argument("--output", required=True, help="Destination MusicXML")
    args = ap.parse_args()

    tree = ET.parse(args.input)
    root = tree.getroot()
    n = apply_mode(root, args.mode, args.action)
    save(tree, args.output)
    print(f"Arbeitsblatt ({args.mode}, {args.action}): changed {n} elements. Wrote {args.output}")

if __name__ == "__main__":
    main()
