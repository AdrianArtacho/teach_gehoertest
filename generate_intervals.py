
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET
from musicxml_utils import get_measures_for_section, first_n_notes_in_measure, note_pitch, set_note_pitch, pitch_to_midi, midi_to_pitch, INTERVAL_TO_SEMITONES, write_tree

def main():
    ap = argparse.ArgumentParser(description="Set the 2nd note at a chosen interval from the 1st in the intervals section.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--section-keyword", default="Intervalle", help="Keyword that marks the intervals section")
    ap.add_argument("--intervals", default="m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8", help="Comma list of intervals")
    ap.add_argument("--direction", default="both", choices=["up","down","both"])
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    allowed = [s.strip() for s in args.intervals.split(",") if s.strip() in INTERVAL_TO_SEMITONES]
    if not allowed:
        allowed = ["M2","m3","P4","P5"]

    tree = ET.parse(args.input)
    root = tree.getroot()

    measures = get_measures_for_section(root, args.section_keyword)
    changed = 0
    for meas in measures:
        notes = first_n_notes_in_measure(meas, n=2)
        if len(notes)<2: 
            continue
        n1, n2 = notes
        p1 = note_pitch(n1)
        if p1 is None: 
            continue
        step, alter, octave = p1
        base_midi = pitch_to_midi(step, alter, octave)
        interval_name = random.choice(allowed)
        semis = INTERVAL_TO_SEMITONES[interval_name]
        if args.direction=="up":
            delta = semis
        elif args.direction=="down":
            delta = -semis
        else:
            delta = semis if random.random()<0.5 else -semis
        target_midi = base_midi + delta
        t_step, t_alter, t_oct = midi_to_pitch(target_midi)
        set_note_pitch(n2, t_step, t_alter, t_oct)
        changed += 1

    write_tree(tree, args.output)
    print(f"Updated {changed} interval prompts in section '{args.section_keyword}'. Wrote {args.output}")

if __name__ == "__main__":
    main()
