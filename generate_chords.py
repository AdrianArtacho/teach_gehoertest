
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET
from musicxml_utils import get_measures_for_section, first_n_notes_in_measure, note_pitch, set_note_pitch, pitch_to_midi, midi_to_pitch, clone_note_as_chord_tone, write_tree
TRIADS={"maj":[0,4,7],"min":[0,3,7],"dim":[0,3,6],"aug":[0,4,8]}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--section-keyword", default="Akkord")
    ap.add_argument("--triads", default="maj,min,dim"); ap.add_argument("--inversion", default="random", choices=["root","first","second","random"])
    ap.add_argument("--seed", type=int, default=None); args=ap.parse_args()
    if args.seed is not None: random.seed(args.seed)
    allowed=[t.strip() for t in args.triads.split(",") if t.strip() in TRIADS] or ["maj","min"]
    tree=ET.parse(args.input); root=tree.getroot()
    measures=get_measures_for_section(root, args.section_keyword); changed=0
    for meas in measures:
        notes=first_n_notes_in_measure(meas,1)
        if not notes: continue
        root_note=notes[0]; p=note_pitch(root_note)
        if p is None: continue
        step,alter,octave=p; base=pitch_to_midi(step,alter,octave)
        kind=random.choice(allowed); ints=TRIADS[kind][:]
        inv=args.inversion if args.inversion!="random" else random.choice(["root","first","second"])
        if inv=="first": ints=[ints[1]-12, ints[2]-12, ints[0]]
        elif inv=="second": ints=[ints[2]-12, ints[0], ints[1]]
        s0,a0,o0=midi_to_pitch(base+ints[0]); set_note_pitch(root_note,s0,a0,o0)
        nB=clone_note_as_chord_tone(root_note); nC=clone_note_as_chord_tone(root_note)
        idx=list(meas).index(root_note); meas.insert(idx+1,nB); meas.insert(idx+2,nC)
        s1,a1,o1=midi_to_pitch(base+ints[1]); s2,a2,o2=midi_to_pitch(base+ints[2])
        set_note_pitch(nB,s1,a1,o1); set_note_pitch(nC,s2,a2,o2); changed+=1
    write_tree(tree,args.output); print(f"Created/updated {changed} chords. Wrote {args.output}")
if __name__=='__main__': main()
