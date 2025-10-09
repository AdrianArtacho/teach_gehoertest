
#!/usr/bin/env python3
import argparse, random, re, xml.etree.ElementTree as ET

def parse_placeholders(s: str):
    result=set()
    for tok in s.split(","):
        tok=tok.strip()
        m = re.fullmatch(r"([A-Ga-g])(?:[#b])?(\d)", tok)
        if not m: continue
        result.add((m.group(1).upper(), int(m.group(2))))
    return result

def find_section_bounds_global(root, keyword):
    markers=[]; 
    for part in root.findall("part"):
        for mi, meas in enumerate(part.findall("measure")):
            for d in meas.findall("direction"):
                for w in d.findall(".//words"):
                    if not (w.text and w.text.strip()): continue
                    txt=w.text.strip()
                    if keyword.lower() in txt.lower(): markers.append(("start", mi))
                    else: markers.append(("other", mi))
    starts=[mi for tag,mi in markers if tag=="start"]
    if not starts: return None
    start=starts[0]; after=[mi for tag,mi in markers if mi>start]
    end=min(after) if after else None
    return (start, end)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--section-keyword", default="Tonleiter")
    ap.add_argument("--accidentals", default="sharp,flat,natural")
    ap.add_argument("--placeholders", default="E4,E5")
    ap.add_argument("--seed", type=int, default=None); args=ap.parse_args()
    if args.seed is not None: random.seed(args.seed)
    acc_choices=[]
    for a in args.accidentals.split(","):
        a=a.strip().lower()
        if a=="sharp": acc_choices.append(1)
        elif a=="flat": acc_choices.append(-1)
        elif a=="natural": acc_choices.append(0)
    if not acc_choices: acc_choices=[0]
    wanted = parse_placeholders(args.placeholders)
    tree=ET.parse(args.input); root=tree.getroot()
    bounds=find_section_bounds_global(root, args.section_keyword); changed=0
    if bounds is not None:
        start,end=bounds
        for part in root.findall("part"):
            measures=part.findall("measure")
            seg=measures[start:end] if end is not None else measures[start:]
            for meas in seg:
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
if __name__=='__main__': main()
