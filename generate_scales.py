
#!/usr/bin/env python3
import argparse
import random
import xml.etree.ElementTree as ET

TAG2ALTER = {"natural": 0, "sharp": 1, "flat": -1}
STEP_TO_INDEX = {'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}
NAT_SEMITONES = [0,2,4,5,7,9,11]

def parse_csv_list(s):
    if not s: return []
    return [t.strip() for t in s.split(",") if t.strip()]

def is_pitched_note(note):
    return note.find("pitch") is not None

def is_visible(note):
    return (note.get("print-object") or "").strip().lower() != "no"

def set_visible(note, yes=True):
    if yes:
        if note.get("print-object") is not None:
            del note.attrib["print-object"]
    else:
        note.set("print-object","no")

def get_step_oct_alter(note):
    p = note.find("pitch")
    if p is None: return None
    step = (p.findtext("step") or "").upper()
    octave_txt = p.findtext("octave")
    if not step or octave_txt is None: return None
    octv = int(octave_txt)
    alt_el = p.find("alter")
    alt = int(float(alt_el.text)) if alt_el is not None and (alt_el.text or "").strip() != "" else 0
    return step, octv, alt

def midi_of(step, octave, alter):
    step_idx = STEP_TO_INDEX[step]
    base = NAT_SEMITONES[step_idx] + 12 * (octave + 1)  # C4 = 60
    return base + alter

def midi_of_note(n):
    so = get_step_oct_alter(n)
    if not so: return -999
    step, octv, alt = so
    return midi_of(step, octv, alt)

def set_alter(note, alter_val):
    p = note.find("pitch")
    if p is None: return
    alt = p.find("alter")
    if alt is None:
        alt = ET.SubElement(p, "alter")
    alt.text = str(int(alter_val))

def clear_explicit_accidental(note):
    for acc in list(note.findall("accidental")):
        note.remove(acc)

def append_profile_to_credit_words(root, profile_name: str):
    if not profile_name: return 0
    prof = profile_name.strip()
    if not prof: return 0
    for cr in root.findall("credit"):
        cw = cr.find("credit-words")
        if cw is not None:
            base = (cw.text or "").strip() or "Title"
            if "(Profile:" not in base:
                cw.text = f"{base} (Profile: {prof})"
            return 1
    credit = ET.Element("credit"); credit.set("page","1")
    cw = ET.SubElement(credit, "credit-words")
    cw.text = f"Title (Profile: {prof})"
    root.insert(0, credit)
    return 1

def main():
    ap = argparse.ArgumentParser(
        description="Scales per-bar anchors: keep first/apex/last visible per measure; alter only hidden notes. Non-selected hidden notes are forced natural."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)

    # Accidentals for altered hidden notes
    ap.add_argument("--accidental-tags", default="", help="Comma list among natural,sharp,flat (default: all three)")
    ap.add_argument("--accidentals", default="", help="(legacy) same as --accidental-tags")

    # Quota across all hidden, non-anchor notes in the whole score
    ap.add_argument("--alter-count", type=int, default=None, help="Exact number of eligible hidden notes to alter")
    ap.add_argument("--alter-ratio", type=float, default=None, help="0..1 ratio of eligible hidden notes to alter (ignored if --alter-count set)")

    # Optional: restrict eligible hidden notes by step+oct name (E4,F4,...) after anchors/visibility applied
    ap.add_argument("--placeholders", default="", help="Comma list of names among HIDDEN notes; empty=all hidden non-anchors")

    # Visibility/anchors
    ap.add_argument("--anchors", default="first,last,apex", help="Anchor kinds to keep visible per bar (comma list)")
    ap.add_argument("--force-anchors-natural", type=str, default="true", help="true|false: set anchors alter=0 and clear courtesy accidentals")

    # Cosmetics
    ap.add_argument("--hide-articulations", type=str, default="true", help="true|false: set print-object='no' on all articulations")
    ap.add_argument("--profile-name", default="", help="Profile label to append in <credit-words>")

    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    tags = parse_csv_list(args.accidental_tags) or parse_csv_list(args.accidentals)
    allowed_alters = []
    for key in ("natural","sharp","flat"):
        if not tags or key in tags:
            allowed_alters.append(TAG2ALTER[key])
    if not allowed_alters:
        allowed_alters = [0, 1, -1]

    placeholders = set(parse_csv_list(args.placeholders))
    anchor_kinds = set(t.strip().lower() for t in parse_csv_list(args.anchors)) or {"first","last","apex"}

    tree = ET.parse(args.input)
    root = tree.getroot()

    # Hide articulations if requested
    if str(args.hide_articulations).strip().lower() in ("1","true","yes","y"):
        hidden = 0
        for art in root.findall(".//notations/articulations/*"):
            if art.get("print-object") != "no":
                art.set("print-object", "no")
                hidden += 1
        if hidden:
            print(f"Articulations hidden: {hidden}")

    if args.profile_name:
        append_profile_to_credit_words(root, args.profile_name)

    # Pass 1: set all pitched notes to hidden by default
    all_pitched = root.findall(".//note[pitch]")
    for n in all_pitched:
        set_visible(n, yes=False)

    # Pass 2: per-measure anchors
    anchors = []
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            notes = [n for n in list(meas) if n.tag == "note" and is_pitched_note(n)]
            if not notes:
                continue
            first = notes[0]
            last  = notes[-1]
            apex  = max(notes, key=lambda nn: midi_of_note(nn))
            selected = []
            if "first" in anchor_kinds: selected.append(first)
            if "last"  in anchor_kinds: selected.append(last)
            if "apex"  in anchor_kinds: selected.append(apex)
            # de-dup
            seen = set(); sel_unique = []
            for n in selected:
                i = id(n)
                if i not in seen:
                    sel_unique.append(n); seen.add(i)
            for n in sel_unique:
                set_visible(n, yes=True)
            anchors.extend(sel_unique)

    # Optionally force anchors to natural
    if str(args.force_anchors_natural).strip().lower() in ("1","true","yes","y"):
        for n in anchors:
            set_alter(n, 0)
            clear_explicit_accidental(n)

    # Pool = all currently HIDDEN pitched notes (non-anchors), optionally filtered by placeholders
    def name_of(note):
        so = get_step_oct_alter(note)
        if not so: return None
        step, octv, _ = so
        return f"{step}{octv}"

    pool = []
    for n in all_pitched:
        if is_visible(n):
            continue
        nm = name_of(n)
        if placeholders and (nm not in placeholders):
            continue
        pool.append(n)

    total_eligible = len(pool)

    # Decide how many to alter
    if args.alter_count is not None:
        k = max(0, min(args.alter_count, total_eligible))
    elif args.alter_ratio is not None:
        ratio = max(0.0, min(1.0, float(args.alter_ratio)))
        k = int(round(ratio * total_eligible))
    else:
        k = total_eligible

    to_alter = set(random.sample(pool, k)) if k > 0 else set()

    changed = 0
    for n in pool:
        if n in to_alter:
            alter = random.choice(allowed_alters)
            set_alter(n, alter)
            clear_explicit_accidental(n)
            changed += 1
        else:
            # FORCE non-selected hidden notes to NATURAL to prevent leftover flats/sharps from the template
            set_alter(n, 0)
            clear_explicit_accidental(n)

    tree.write(args.output, encoding='utf-8', xml_declaration=True)
    print(f"Per-bar anchors kept visible: {len(anchors)}; changed {changed} / {total_eligible} hidden notes. Wrote {args.output}")

if __name__ == "__main__":
    main()
