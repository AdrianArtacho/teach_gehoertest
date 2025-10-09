
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

def parse_scalar(v):
    v=v.strip()
    if v.startswith(("'", '"')) and v.endswith(("'", '"')) and len(v)>=2:
        return v[1:-1]
    if v.lower() in ("true","false"): return v.lower()=="true"
    try:
        if "." in v: return float(v)
        return int(v)
    except: pass
    if v.startswith("[") and v.endswith("]"):
        inner=v[1:-1].strip()
        if not inner: return []
        return [parse_scalar(p.strip()) for p in inner.split(",") ]
    return v

def parse_yaml_min(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    root = {}
    stack = [(0, root)]
    last_keys = {id(root): None}
    for raw in lines:
        line = raw.split("#",1)[0].rstrip()
        if not line.strip(): continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0: raise ValueError("Indentation must be multiples of 2 spaces")
        key, sep, rest = line.strip().partition(":")
        if not sep: raise ValueError("Expected ':' in line")
        while stack and indent < stack[-1][0]:
            stack.pop()
        if indent > stack[-1][0]:
            parent = stack[-1][1]
            lk = last_keys.get(id(parent))
            if lk is None:
                raise ValueError("Malformed YAML: unexpected indentation")
            child = {}
            parent[lk] = child
            stack.append((indent, child))
            last_keys[id(child)] = None
        current = stack[-1][1]
        if rest.strip()=="":
            current[key] = current.get(key, {})
            last_keys[id(current)] = key
        else:
            current[key] = parse_scalar(rest)
            last_keys[id(current)] = key
    return root

def deep_merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k,v in override.items():
            out[k] = deep_merge(base.get(k), v) if k in base else v
        return out
    return override

def load_config(path: Path, profile: str=None):
    d = parse_yaml_min(path)
    cfg = {
        "inputs": {
            "scales": d.get("inputs", {}).get("scales", "sibelius/Hoeren_scales.musicxml"),
            "intervals": d.get("inputs", {}).get("intervals", "sibelius/Hoeren_intervals.musicxml"),
            "chords": d.get("inputs", {}).get("chords", "sibelius/Hoeren_chords.musicxml"),
            "rhythms": d.get("inputs", {}).get("rhythms", "sibelius/Hoeren_rhythm.musicxml"),
        },
        "outdir": d.get("outdir", "OUT"),
        "seed": d.get("seed", 42),
        "what": d.get("what", "all"),
        "scales": {
            "accidentals": ",".join(d.get("scales", {}).get("accidentals", ["sharp","flat","natural"])) if isinstance(d.get("scales", {}).get("accidentals"), list) else d.get("scales", {}).get("accidentals", "sharp,flat,natural"),
            "placeholders": ",".join(d.get("scales", {}).get("placeholders", ["E4","E5"])) if isinstance(d.get("scales", {}).get("placeholders"), list) else d.get("scales", {}).get("placeholders", "E4,E5"),
        },
        "intervals": {
            "intervals": ",".join(d.get("intervals", {}).get("set", ["m2","M2","m3","M3","P4","TT","P5","m6","M6","m7","M7","P8"])) if isinstance(d.get("intervals", {}).get("set"), list) else d.get("intervals", {}).get("set", "m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8"),
            "direction": d.get("intervals", {}).get("direction", "both"),
        },
        "chords": {
            "triads": ",".join(d.get("chords", {}).get("triads", ["maj","min","dim"])) if isinstance(d.get("chords", {}).get("triads"), list) else d.get("chords", {}).get("triads", "maj,min,dim"),
            "inversion": d.get("chords", {}).get("inversion", "random"),
        },
        "rhythms": {
            "note_prob": d.get("rhythms", {}).get("note_prob", 0.7),
        },
        "profiles": d.get("profiles", {}),
        "worksheet": {
            "scales": d.get("worksheet", {}).get("scales", "hide"),
            "intervals": d.get("worksheet", {}).get("intervals", "hide"),
            "chords": d.get("worksheet", {}).get("chords", "hide"),
            "rhythms": d.get("worksheet", {}).get("rhythms", "hide"),
        },
    }
    if profile:
        prof = cfg["profiles"].get(profile)
        if prof:
            cfg = deep_merge(cfg, prof)
    return cfg

def main():
    ap = argparse.ArgumentParser(description="Übungsblatt CLI (per-section inputs + profiles)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--outdir"); ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    cfg = load_config(Path(args.config), args.profile)
    if args.outdir: cfg["outdir"] = args.outdir
    if args.seed is not None: cfg["seed"] = args.seed

    outdir = Path(cfg["outdir"]).resolve(); outdir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg["seed"])

    def p(rel): return str(Path(rel).resolve())

    what = cfg.get("what","all")
    if what in ("all","scales"):
        run([sys.executable, HERE / "generate_scales.py",
             "--input", p(cfg["inputs"]["scales"]),
             "--output", outdir / "Hoeren_scales.musicxml",
             "--accidentals", cfg["scales"]["accidentals"],
             "--placeholders", cfg["scales"]["placeholders"],
             "--seed", seed + 1])

    if what in ("all","intervals"):
        run([sys.executable, HERE / "generate_intervals.py",
             "--input", p(cfg["inputs"]["intervals"]),
             "--output", outdir / "Hoeren_intervals.musicxml",
             "--intervals", cfg["intervals"]["intervals"],
             "--direction", cfg["intervals"]["direction"],
             "--seed", seed + 2])

    if what in ("all","chords"):
        run([sys.executable, HERE / "generate_chords.py",
             "--input", p(cfg["inputs"]["chords"]),
             "--output", outdir / "Hoeren_chords.musicxml",
             "--triads", cfg["chords"]["triads"],
             "--inversion", cfg["chords"]["inversion"],
             "--seed", seed + 3])

    if what in ("all","rhythms"):
        run([sys.executable, HERE / "generate_rhythms.py",
             "--input", p(cfg["inputs"]["rhythms"]),
             "--output", outdir / "Hoeren_rhythm.musicxml",
             "--note-prob", cfg["rhythms"]["note_prob"],
             "--seed", seed + 4])

        # Also produce Arbeitsblatt variants
    ws = HERE / "make_arbeitsblatt.py"
    # scales
    if what in ("all","scales"):
        run([sys.executable, ws, "--mode", "scales", "--input", outdir / "Hoeren_scales.musicxml", "--output", outdir / "Hoeren_scales_arbeitsblatt.musicxml"])
    # intervals
    if what in ("all","intervals"):
        run([sys.executable, ws, "--mode", "intervals", "--input", outdir / "Hoeren_intervals.musicxml", "--output", outdir / "Hoeren_intervals_arbeitsblatt.musicxml"])
    # chords
    if what in ("all","chords"):
        run([sys.executable, ws, "--mode", "chords", "--input", outdir / "Hoeren_chords.musicxml", "--output", outdir / "Hoeren_chords_arbeitsblatt.musicxml"])
    # rhythms
    if what in ("all","rhythms"):
        run([sys.executable, ws, "--mode", "rhythms", "--input", outdir / "Hoeren_rhythm.musicxml", "--output", outdir / "Hoeren_rhythm_arbeitsblatt.musicxml"])
        # Also produce Arbeitsblatt variants with configured actions
    ws = HERE / "make_arbeitsblatt.py"
    if what in ("all","scales"):
        run([sys.executable, ws, "--mode", "scales", "--action", cfg["worksheet"]["scales"], "--input", outdir / "Hoeren_scales.musicxml", "--output", outdir / "Hoeren_scales_arbeitsblatt.musicxml"])
    if what in ("all","intervals"):
        run([sys.executable, ws, "--mode", "intervals", "--action", cfg["worksheet"]["intervals"], "--input", outdir / "Hoeren_intervals.musicxml", "--output", outdir / "Hoeren_intervals_arbeitsblatt.musicxml"])
    if what in ("all","chords"):
        run([sys.executable, ws, "--mode", "chords", "--action", cfg["worksheet"]["chords"], "--input", outdir / "Hoeren_chords.musicxml", "--output", outdir / "Hoeren_chords_arbeitsblatt.musicxml"])
    if what in ("all","rhythms"):
        run([sys.executable, ws, "--mode", "rhythms", "--action", cfg["worksheet"]["rhythms"], "--input", outdir / "Hoeren_rhythm.musicxml", "--output", outdir / "Hoeren_rhythm_arbeitsblatt.musicxml"])
    print(f"Done. Files saved to {outdir}")

if __name__ == "__main__":
    main()
