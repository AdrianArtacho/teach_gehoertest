
#!/usr/bin/env python3
import argparse
import xml.etree.ElementTree as ET

def save(tree, path):
    tree.write(path, encoding="utf-8", xml_declaration=True)

# ----- Scales: hide *all* accidentals (keep playback) -----
def scales_hide(root):
    """Make all accidentals invisible. If a pitch has <alter> but no <accidental>, add an invisible one."""
    def accidental_text_from_alter(alt):
        try:
            a = int(float(str(alt).strip()))
        except Exception:
            return None
        return {-2:"flat-flat", -1:"flat", 0:"natural", 1:"sharp", 2:"sharp-sharp"}.get(a)

    changed = 0
    for note in root.findall(".//note"):
        had = False
        for acc in list(note.findall("accidental")):
            acc.set("print-object", "no"); had = True; changed += 1
        if not had:
            p = note.find("pitch")
            if p is not None:
                alt = p.find("alter")
                if alt is not None and (alt.text or "").strip() != "":
                    txt = accidental_text_from_alter(alt.text)
                    if txt is not None and txt != "natural":
                        acc = ET.SubElement(note, "accidental", {"print-object": "no"})
                        acc.text = txt; changed += 1
    return changed

def scales_delete(root):
    # Not meaningful; behave same as hide.
    return scales_hide(root)

# ----- Intervals -----
def intervals_hide(root):
    hidden = 0
    for note in root.findall(".//note"):
        typ = (note.findtext("type") or "").strip().lower()
        if typ == "quarter":
            note.set("print-object", "no"); hidden += 1
    return hidden

def intervals_delete(root):
    removed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                typ = (note.findtext("type") or "").strip().lower()
                if typ == "quarter":
                    meas.remove(note); removed += 1
    return removed

# ----- Chords -----
def _staff_num(note):
    s = note.findtext("staff")
    return int(s) if s and s.isdigit() else None

def chords_hide(root):
    saw_staff = False; hidden = 0
    for note in root.findall(".//note"):
        sn = _staff_num(note)
        if sn is not None:
            saw_staff = True
            if sn == 1:
                note.set("print-object", "no"); hidden += 1
    if not saw_staff:
        for note in root.findall(".//note"):
            if note.find("chord") is not None:
                note.set("print-object", "no"); hidden += 1
    return hidden

def chords_delete(root):
    saw_staff = False; removed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in list(meas.findall("note")):
                sn = _staff_num(note)
                if sn is not None:
                    saw_staff = True
                    if sn == 1:
                        meas.remove(note); removed += 1
    if not saw_staff:
        for part in root.findall("part"):
            for meas in part.findall("measure"):
                for note in list(meas.findall("note")):
                    if note.find("chord") is not None:
                        meas.remove(note); removed += 1
    return removed

# ----- Rhythms -----
def _strip_visual_children(note):
    for tag in ["beam","flag","stem","notehead","accidental","dot"]:
        for el in list(note.findall(tag)):
            note.remove(el)
    for el in list(note.findall("tie")):
        note.remove(el)
    notations = note.find("notations")
    if notations is not None:
        note.remove(notations)

def rhythms_hide(root):
    """
    Render nothing in rhythm Arbeitsblatt:
      - Remove all <backup> (no multi-voice rewinds).
      - Replace every <note> with <forward> of equal duration (advances time, draws nothing).
    """
    changed = 0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            # Remove any voice rewinds to avoid corrupt timing
            for b in list(meas.findall("backup")):
                meas.remove(b)

            # Replace notes with forward (same duration)
            for note in list(meas.findall("note")):
                dur_el = note.find("duration")
                fwd = ET.Element("forward")
                d = ET.SubElement(fwd, "duration")
                # Use the note's duration if present; fallback to '1'
                d.text = (dur_el.text if dur_el is not None and (dur_el.text or "").strip() else "1")
                idx = list(meas).index(note)
                meas.insert(idx, fwd)
                meas.remove(note)
                changed += 1
    return changed

def rhythms_delete(root):
    changed = 0
    for note in root.findall(".//note"):
        p = note.find("pitch")
        if p is not None:
            note.remove(p)
            if note.find("rest") is None:
                ET.SubElement(note, "rest")
            _strip_visual_children(note); changed += 1
    return changed

# ----- Dispatch -----
def apply_mode(root, page, action):
    if page == "scales": return (scales_hide if action=="hide" else scales_delete)(root)
    if page == "intervals": return (intervals_hide if action=="hide" else intervals_delete)(root)
    if page == "chords": return (chords_hide if action=="hide" else chords_delete)(root)
    if page == "rhythms": return (rhythms_hide if action=="hide" else rhythms_delete)(root)
    raise ValueError("unknown page" )

def main():
    ap = argparse.ArgumentParser(description="Create worksheet/Arbeitsblatt variants (hide or delete)." )
    ap.add_argument("--mode", required=True, choices=["scales","intervals","chords","rhythms"])
    ap.add_argument("--action", default="hide", choices=["hide","delete"])
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    tree = ET.parse(args.input); root = tree.getroot()
    n = apply_mode(root, args.mode, args.action)
    save(tree, args.output)
    print(f"Arbeitsblatt ({args.mode}, {args.action}): changed {n} elements. Wrote {args.output}")

if __name__ == "__main__":
    main()
