
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET

def find_section_bounds_global(root, keyword):
    # returns (start_idx, end_idx_exclusive) based on any part that has a <words> with the keyword
    markers = []
    parts = root.findall("part")
    for pi, part in enumerate(parts):
        for mi, meas in enumerate(part.findall("measure")):
            for d in meas.findall("direction"):
                for w in d.findall(".//words"):
                    if w.text and keyword.lower() in w.text.lower():
                        markers.append(("start", mi))
                    elif w.text:
                        markers.append(("other", mi))
    # pick first 'start', and next marker after it
    starts = [mi for tag, mi in markers if tag=="start"]
    if not starts:
        return None
    start = starts[0]
    after = [mi for tag, mi in markers if mi>start]
    end = min(after) if after else None
    return (start, end)

def main():
    ap = argparse.ArgumentParser(description="Randomize accidentals of E4/E5 placeholders in the scales section.")
    ap.add_argument("--input", required=True, help="Template MusicXML file")
    ap.add_argument("--output", required=True, help="Output MusicXML file")
    ap.add_argument("--section-keyword", default="Tonleiter", help="Keyword (in <words>) that marks the scales section")
    ap.add_argument("--accidentals", default="sharp,flat,natural", help="Comma list among: sharp,flat,natural")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    acc_choices = []
    for a in args.accidentals.split(","):
        a=a.strip().lower()
        if a=="sharp": acc_choices.append(1)
        elif a=="flat": acc_choices.append(-1)
        elif a=="natural": acc_choices.append(0)
    if not acc_choices:
        acc_choices = [0]

    tree = ET.parse(args.input)
    root = tree.getroot()

    bounds = find_section_bounds_global(root, args.section_keyword)
    changed = 0
    if bounds is not None:
        start, end = bounds
        parts = root.findall("part")
        for part in parts:
            measures = part.findall("measure")
            segment = measures[start:end] if end is not None else measures[start:]
            for meas in segment:
                for note in meas.findall("note"):
                    p = note.find("pitch")
                    if p is None:
                        continue
                    step = p.findtext("step")
                    octave = p.findtext("octave")
                    if step=="E" and octave in ("4","5"):
                        alter = random.choice(acc_choices)
                        # write back
                        step_el = p.find("step"); step_el.text = "E"
                        alter_el = p.find("alter")
                        if alter==0:
                            if alter_el is not None:
                                p.remove(alter_el)
                        else:
                            if alter_el is None:
                                alter_el = ET.SubElement(p, "alter")
                            alter_el.text = str(int(alter))
                        octave_el = p.find("octave"); octave_el.text = octave
                        changed += 1

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} E notes in section '{args.section_keyword}'. Wrote {args.output}")

if __name__ == "__main__":
    main()
