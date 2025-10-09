
#!/usr/bin/env python3
import argparse, xml.etree.ElementTree as ET

def save(tree, path):
    tree.write(path, encoding="utf-8", xml_declaration=True)

def _staff_num(note):
    s = note.findtext("staff")
    return int(s) if s and s.isdigit() else None

# ---------------- Scales ----------------
def scales_hide(root):
    changed=0
    for note in root.findall(".//note"):
        p = note.find("pitch")
        if p is not None:
            alt = p.find("alter")
            if alt is not None:
                p.remove(alt); changed+=1
        acc = note.find("accidental")
        if acc is not None:
            note.remove(acc); changed+=1
    return changed

def scales_delete(root):
    # same effect as hide for scales
    return scales_hide(root)

# ---------------- Intervals ----------------
def intervals_hide(root):
    hidden=0
    for note in root.findall(".//note"):
        typ = (note.findtext("type") or "").strip().lower()
        if typ == "quarter":
            note.set("print-object","no"); hidden+=1
    return hidden

def intervals_delete(root):
    removed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                typ = (note.findtext("type") or "").strip().lower()
                if typ == "quarter":
                    meas.remove(note); removed+=1
    return removed

# ---------------- Chords ----------------
def chords_hide(root):
    # Hide ALL notes in the upper staff (staff==1), leave lower staff visible.
    # Fallback: if no staff info, hide chord tones (notes carrying <chord/>).
    saw_staff=False
    hidden=0
    for note in root.findall(".//note"):
        sn = _staff_num(note)
        if sn is not None:
            saw_staff=True
            if sn == 1:
                note.set("print-object","no"); hidden+=1
    if not saw_staff:
        # fallback to chord tones
        for note in root.findall(".//note"):
            if note.find("chord") is not None:
                note.set("print-object","no"); hidden+=1
    return hidden

def chords_delete(root):
    # Delete ALL notes in the upper staff (staff==1). Fallback: delete chord tones.
    saw_staff=False
    removed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                sn = _staff_num(note)
                if sn is not None:
                    saw_staff=True
                    if sn == 1:
                        meas.remove(note); removed+=1
    if not saw_staff:
        for part in root.findall("part"):
            for meas in part.findall("measure"):
                for note in list(meas.findall("note")):
                    if note.find("chord") is not None:
                        meas.remove(note); removed+=1
    return removed

# ---------------- Rhythms ----------------
def _strip_visual_children(note):
    # Remove beams, flags, stems, noteheads, ties/tieds, notations, and accidentals/dots for safety
    for tag in ["beam","flag","stem","notehead","accidental","dot"]:
        for el in list(note.findall(tag)):
            note.remove(el)
    # Remove ties
    for el in list(note.findall("tie")):
        note.remove(el)
    notations = note.find("notations")
    if notations is not None:
        note.remove(notations)

def rhythms_hide(root):
    # Hide all notes AND their visual connectors (beams, stems, flags, etc.).
    hidden=0
    for note in root.findall(".//note"):
        if note.find("pitch") is not None:
            note.set("print-object","no")
            _strip_visual_children(note)
            hidden+=1
    return hidden

def rhythms_delete(root):
    # Convert all pitched notes to rests (preserve duration), and strip visual children.
    changed=0
    for note in root.findall(".//note"):
        p = note.find("pitch")
        if p is not None:
            note.remove(p)
            if note.find("rest") is None:
                ET.SubElement(note, "rest")
            _strip_visual_children(note)
            changed+=1
    return changed

# ---------------- Dispatch ----------------
def apply_mode(root, page, action):
    if page=="scales":
        return (scales_hide if action=="hide" else scales_delete)(root)
    if page=="intervals":
        return (intervals_hide if action=="hide" else intervals_delete)(root)
    if page=="chords":
        return (chords_hide if action=="hide" else chords_delete)(root)
    if page=="rhythms":
        return (rhythms_hide if action=="hide" else rhythms_delete)(root)
    raise ValueError("unknown page")

def main():
    ap = argparse.ArgumentParser(description="Create worksheet/Arbeitsblatt variants (hide or delete).")
    ap.add_argument("--mode", required=True, choices=["scales","intervals","chords","rhythms"], help="Which page type")
    ap.add_argument("--action", default="hide", choices=["hide","delete"], help="hide or delete solutions")
    ap.add_argument("--input", required=True, help="Source MusicXML")
    ap.add_argument("--output", required=True, help="Destination MusicXML")
    args = ap.parse_args()

    tree = ET.parse(args.input); root = tree.getroot()
    n = apply_mode(root, args.mode, args.action)
    save(tree, args.output)
    print(f"Arbeitsblatt ({args.mode}, {args.action}): changed {n} elements. Wrote {args.output}")

if __name__ == "__main__":
    main()
