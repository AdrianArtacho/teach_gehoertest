
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET
from musicxml_utils import get_measures_for_section, write_tree

def main():
    ap = argparse.ArgumentParser(description="Randomize note/rest patterns in the rhythms section while preserving durations.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--section-keyword", default="Rhythmus", help="Keyword that marks the rhythms section")
    ap.add_argument("--note-prob", type=float, default=0.7, help="Probability of a note vs rest at each slot")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    tree = ET.parse(args.input)
    root = tree.getroot()

    measures = get_measures_for_section(root, args.section_keyword)
    changed = 0
    for meas in measures:
        for n in list(meas.findall("note")):
            dur = n.find("duration")
            if random.random() < args.note_prob:
                # ensure note with default G4 if missing pitch
                r = n.find("rest")
                if r is not None:
                    n.remove(r)
                if n.find("pitch") is None:
                    p = ET.SubElement(n, "pitch")
                    ET.SubElement(p, "step").text = "G"
                    ET.SubElement(p, "octave").text = "4"
            else:
                p = n.find("pitch")
                if p is not None:
                    n.remove(p)
                if n.find("rest") is None:
                    ET.SubElement(n, "rest")
            changed += 1

    write_tree(tree, args.output)
    print(f"Randomized {changed} note/rest slots in section '{args.section_keyword}'. Wrote {args.output}")

if __name__ == "__main__":
    main()
