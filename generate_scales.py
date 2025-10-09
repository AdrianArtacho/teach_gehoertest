
#!/usr/bin/env python3
import argparse, random, re, xml.etree.ElementTree as ET

def parse_placeholders(s: str):
    result=set()
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    for tok in s.split(','):
        tok = tok.strip().strip("'\"")
        m = re.fullmatch(r"([A-Ga-g])(?:[#b])?(\d)", tok)
        if not m: 
            continue
        result.add((m.group(1).upper(), int(m.group(2))))
    return result

def main():
    ap=argparse.ArgumentParser(description="Randomize accidentals on selected placeholders across the entire file.")
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--accidentals", default="sharp,flat,natural")
    ap.add_argument("--placeholders", default="E4,E5")
    ap.add_argument("--seed", type=int, default=None)
    args=ap.parse_args()

    if args.seed is not None: random.seed(args.seed)

    acc_choices = []
    for a in args.accidentals.split(','):
        a=a.strip().lower()
        if a=="sharp": acc_choices.append(1)
        elif a=="flat": acc_choices.append(-1)
        elif a=="natural": acc_choices.append(0)
    if not acc_choices: acc_choices=[0]

    wanted = parse_placeholders(args.placeholders)

    tree=ET.parse(args.input); root=tree.getroot()
    changed=0
    for part in root.findall("part"):
        for meas in part.findall("measure"):
            for note in meas.findall("note"):
                p=note.find("pitch")
                if p is None: continue
                step=(p.findtext("step") or "").upper()
                octave=p.findtext("octave")
                if not octave: continue
                try: octi=int(octave)
                except: continue
                if (step, octi) in wanted:
                    alter=random.choice(acc_choices)
                    step_el=p.find("step"); step_el.text=step
                    alter_el=p.find("alter")
                    if alter==0:
                        if alter_el is not None: p.remove(alter_el)
                    else:
                        if alter_el is None: alter_el=ET.SubElement(p,"alter")
                        alter_el.text=str(int(alter))
                    oct_el=p.find("octave"); oct_el.text=str(octi)
                    changed+=1

    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"Changed {changed} notes matching {sorted(wanted)}. Wrote {args.output}")

if __name__=='__main__':
    main()
