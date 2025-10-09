
#!/usr/bin/env python3
import argparse, xml.etree.ElementTree as ET

def save(tree, path):
    tree.write(path, encoding="utf-8", xml_declaration=True)

def scales_hide(root):
    # Conceal accidentals by removing <alter> and <accidental> so nothing prints.
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
    # Same as hide for scales; deleting the accidental glyphs is the practical way to conceal.
    return scales_hide(root)

def intervals_hide(root):
    # Hide quarter notes (leave whole ones) with print-object="no"
    hidden=0
    for note in root.findall(".//note"):
        typ = (note.findtext("type") or "").strip().lower()
        if typ == "quarter":
            note.set("print-object","no"); hidden+=1
    return hidden

def intervals_delete(root):
    # Remove quarter notes completely
    removed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                typ = (note.findtext("type") or "").strip().lower()
                if typ == "quarter":
                    meas.remove(note); removed+=1
    return removed

def chords_hide(root):
    # Hide all chord tones (notes with <chord/>) keep bass/root visible
    hidden=0
    for note in root.findall(".//note"):
        if note.find("chord") is not None:
            note.set("print-object","no"); hidden+=1
    return hidden

def chords_delete(root):
    # Delete chord tones (notes with <chord/>)
    removed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                if note.find("chord") is not None:
                    meas.remove(note); removed+=1
    return removed

def rhythms_hide(root):
    # Hide all pitched notes by setting print-object="no" (rests usually remain visible)
    hidden=0
    for note in root.findall(".//note"):
        if note.find("pitch") is not None:
            note.set("print-object","no"); hidden+=1
    return hidden

def rhythms_delete(root):
    # Convert all pitched notes to rests (preserve duration so bars stay intact)
    changed=0
    for note in root.findall(".//note"):
        p = note.find("pitch")
        if p is not None:
            note.remove(p); changed+=1
        if note.find("rest") is None:
            ET.SubElement(note, "rest")
    return changed

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
