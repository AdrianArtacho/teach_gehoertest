
#!/usr/bin/env python3
import argparse, random, xml.etree.ElementTree as ET
from musicxml_utils import get_measures_for_section, first_n_notes_in_measure, note_pitch, set_note_pitch, pitch_to_midi, midi_to_pitch, clone_note_as_chord_tone, write_tree

TRIADS = {
    "maj": [0,4,7],
    "min": [0,3,7],
    "dim": [0,3,6],
    "aug": [0,4,8]
}

def main():
    ap = argparse.ArgumentParser(description="Turn single notes into stacked triads in the chords section.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--section-keyword", default="Akkord", help="Keyword that marks the chords section (e.g., 'Akkord' or 'Dreiklang')")
    ap.add_argument("--triads", default="maj,min,dim", help="Comma list among: maj,min,dim,aug")
    ap.add_argument("--inversion", default="root", choices=["root","first","second","random"], help="Inversion for the triad")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    allowed = [t.strip() for t in args.triads.split(",") if t.strip() in TRIADS]
    if not allowed:
        allowed = ["maj","min"]

    tree = ET.parse(args.input)
    root = tree.getroot()

    measures = get_measures_for_section(root, args.section_keyword)
    changed = 0
    for meas in measures:
        notes = first_n_notes_in_measure(meas, n=1)
        if not notes:
            continue
        root_note = notes[0]
        p = note_pitch(root_note)
        if p is None:
            continue
        step, alter, octave = p
        root_midi = pitch_to_midi(step, alter, octave)
        triad_kind = random.choice(allowed)
        intervals = TRIADS[triad_kind][:]
        inv_choice = args.inversion
        if inv_choice=="random":
            inv_choice = random.choice(["root","first","second"])
        if inv_choice=="first":
            intervals = [intervals[1]-12, intervals[2]-12, intervals[0]]
        elif inv_choice=="second":
            intervals = [intervals[2]-12, intervals[0], intervals[1]]

        # adjust root to interval[0]
        set_note_pitch(root_note, *midi_to_pitch(root_midi + intervals[0]))
        # add two chord tones
        note_b = clone_note_as_chord_tone(root_note)
        note_c = clone_note_as_chord_tone(root_note)
        parent = meas
        idx = list(parent).index(root_note)
        parent.insert(idx+1, note_b)
        parent.insert(idx+2, note_c)
        from_midi = root_midi
        # set their pitches
        step_b, alt_b, oct_b = midi_to_pitch(from_midi + intervals[1])
        step_c, alt_c, oct_c = midi_to_pitch(from_midi + intervals[2])
        set_note_pitch(note_b, step_b, alt_b, oct_b)
        set_note_pitch(note_c, step_c, alt_c, oct_c)
        changed += 1

    write_tree(tree, args.output)
    print(f"Created/updated {changed} chords in section '{args.section_keyword}'. Wrote {args.output}")

if __name__ == "__main__":
    main()
