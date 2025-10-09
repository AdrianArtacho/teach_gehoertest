
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET
from musicxml_utils import write_tree
def main():
    ap=argparse.ArgumentParser(description="Randomize note/rest patterns across the entire file while preserving durations.")
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--note-prob", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=None); args=ap.parse_args()
    if args.seed is not None: random.seed(args.seed)
    tree=ET.parse(args.input); root=tree.getroot(); changed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for n in list(meas.findall("note")):
                if random.random()<args.note_prob:
                    r=n.find("rest")
                    if r is not None: n.remove(r)
                    if n.find("pitch") is None:
                        p=ET.SubElement(n,"pitch"); ET.SubElement(p,"step").text="G"; ET.SubElement(p,"octave").text="4"
                else:
                    p=n.find("pitch")
                    if p is not None: n.remove(p)
                    if n.find("rest") is None: ET.SubElement(n,"rest")
                changed+=1
    write_tree(tree,args.output); print(f"Randomized {changed} rhythm slots. Wrote {args.output}")
if __name__=='__main__': main()
