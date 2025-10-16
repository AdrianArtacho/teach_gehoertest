
#!/usr/bin/env python3
import argparse
import random
import xml.etree.ElementTree as ET

TAG2ALTER = {"natural": 0, "sharp": 1, "flat": -1}

def parse_csv_list(s):
    if not s: return []
    return [t.strip() for t in s.split(",") if t.strip()]

def is_pitched_note(note):
    return note.find("pitch") is not None

def is_invisible(note):
    # MusicXML: <note print-object="no"> ... </note>
    return (note.get("print-object") or "").strip().lower() == "no"

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

def main():
    ap = argparse.ArgumentParser(
        description="Generate scales: alter ONLY invisible (print-object='no') notes; visible notes remain unchanged."
    )
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)

    # Allowed accidental set for altered (invisible) notes
    ap.add_argument("--accidental-tags", default="", help="Comma list among natural,sharp,flat (default: all three)")
    ap.add_argument("--accidentals", default="", help="(legacy) same as --accidental-tags")

    # Quota of how many invisible notes to alter
    ap.add_argument("--alter-count", type=int, default=None, help="Exact number of eligible invisible notes to alter")
    ap.add_argument("--alter-ratio", type=float, default=None, help="0..1 ratio of eligible invisible notes to alter (ignored if --alter-count set)")

    # Optional: restrict which invisible notes are eligible by name
    ap.add_argument("--placeholders", default="", help="Comma list of step+oct names (E4,F4,...) among INVISIBLE notes; empty=all (excluding first/last invisible)")

    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Allowed accidentals for altered notes
    tags = parse_csv_list(args.accidental_tags) or parse_csv_list(args.accidentals)
    allowed_alters = []
    for key in ("natural","sharp","flat"):
        if not tags or key in tags:
            allowed_alters.append(TAG2ALTER[key])
    if not allowed_alters:
        allowed_alters = [0, 1, -1]

    placeholders = set(parse_csv_list(args.placeholders))

    tree = ET.parse(args.input)
    root = tree.getroot()

    # Collect ONLY invisible pitched notes in reading order
    inv_notes = [n for n in root.findall(".//note") if is_pitched_note(n) and is_invisible(n)]

    if not inv_notes:
        # Nothing to do; leave file as-is
        tree.write(args.output, encoding="utf-8", xml_declaration=True)
        print(f"Changed 0 notes (no invisible notes found). Wrote {args.output}")
        return

    # First and last invisible notes are forced natural and excluded from alteration
    first_inv = inv_notes[0]
    last_inv  = inv_notes[-1]
    for endpoint in (first_inv, last_inv):
        set_alter(endpoint, 0)
        clear_explicit_accidental(endpoint)

    # Eligible pool = invisible notes excluding endpoints; optional placeholder filter
    def name_of(note):
        so = get_step_oct_alter(note)
        if not so: return None
        step, octv, _ = so
        return f"{step}{octv}"

    pool = []
    for n in inv_notes[1:-1]:
        nm = name_of(n)
        if placeholders and (nm not in placeholders):
            continue
        pool.append(n)

    total_eligible = len(pool)

    # Determine how many to alter
    if args.alter_count is not None:
        k = max(0, min(args.alter_count, total_eligible))
    elif args.alter_ratio is not None:
        ratio = max(0.0, min(1.0, float(args.alter_ratio)))
        k = int(round(ratio * total_eligible))
    else:
        k = total_eligible  # default: alter all eligible invisible notes

    # Sample and apply
    to_alter = set(random.sample(pool, k)) if k > 0 else set()

    changed = 0
    for n in pool:
        if n in to_alter:
            alter = random.choice(allowed_alters)
            set_alter(n, alter)
            clear_explicit_accidental(n)
            changed += 1
        # else: leave invisible note's accidental as-is

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} / {total_eligible} eligible invisible notes. Wrote {args.output}")

if __name__ == "__main__":
    main()
