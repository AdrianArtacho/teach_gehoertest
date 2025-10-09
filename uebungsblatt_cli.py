
#!/usr/bin/env python3
import argparse, sys
from pathlib import Path
import subprocess

HERE = Path(__file__).parent.resolve()

def run(cmd):
    print(">", " ".join(str(c) for c in cmd))
    res = subprocess.run([str(c) for c in cmd], text=True, capture_output=True)
    if res.stdout: print(res.stdout.strip())
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

def main():
    ap = argparse.ArgumentParser(description="Übungsblatt CLI")
    ap.add_argument("--input", default="sibelius/Hoeren_1.musicxml")
    ap.add_argument("--outdir", default="OUT")
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--scales-section", default="Tonleiter")
    ap.add_argument("--scales-accidentals", default="sharp,flat,natural")
    ap.add_argument("--scales-placeholders", default="E4,E5")

    ap.add_argument("--intervals-section", default="Intervalle")
    ap.add_argument("--intervals", default="m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8")
    ap.add_argument("--intervals-direction", default="both", choices=["up","down","both"])

    ap.add_argument("--chords-section", default="Akkord")
    ap.add_argument("--chords-triads", default="maj,min,dim")
    ap.add_argument("--chords-inversion", default="random", choices=["root","first","second","random"])

    ap.add_argument("--rhythms-section", default="Rhythmus")
    ap.add_argument("--rhythms-note-prob", type=float, default=0.7)

    ap.add_argument("--what", default="all", choices=["all","scales","intervals","chords","rhythms"])
    args = ap.parse_args()

    inp = Path(args.input).resolve()
    outdir = Path(args.outdir).resolve(); outdir.mkdir(parents=True, exist_ok=True)

    if args.what in ("all","scales"):
        run([sys.executable, HERE / "generate_scales.py",
             "--input", inp, "--output", outdir / "Hoeren_1_scales.musicxml",
             "--section-keyword", args.scales_section,
             "--accidentals", args.scales_accidentals,
             "--placeholders", args.scales-placeholders if hasattr(args, 'scales-placeholders') else args.scales_placeholders,
             "--seed", args.seed + 1])

    if args.what in ("all","intervals"):
        run([sys.executable, HERE / "generate_intervals.py",
             "--input", inp, "--output", outdir / "Hoeren_1_intervals.musicxml",
             "--section-keyword", args.intervals_section,
             "--intervals", args.intervals,
             "--direction", args.intervals_direction,
             "--seed", args.seed + 2])

    if args.what in ("all","chords"):
        run([sys.executable, HERE / "generate_chords.py",
             "--input", inp, "--output", outdir / "Hoeren_1_chords.musicxml",
             "--section-keyword", args.chords_section,
             "--triads", args.chords_triads,
             "--inversion", args.chords_inversion,
             "--seed", args.seed + 3])

    if args.what in ("all","rhythms"):
        run([sys.executable, HERE / "generate_rhythms.py",
             "--input", inp, "--output", outdir / "Hoeren_1_rhythms.musicxml",
             "--section-keyword", args.rhythms_section,
             "--note-prob", args.rhythms_note_prob,
             "--seed", args.seed + 4])

    print(f"Done. Files saved to {outdir}")

if __name__ == "__main__":
    main()
