
#!/usr/bin/env python3
import argparse, sys, re
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

def parse_scalar(val):
    v = val.strip()
    if v.startswith(("'", '"')) and v.endswith(("'", '"')) and len(v)>=2:
        return v[1:-1]
    if v.lower() in ("true","false"): return v.lower()=="true"
    # int/float
    try:
        if "." in v: return float(v)
        return int(v)
    except:
        pass
    # list in [a,b,c] form
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [parse_scalar(p) for p in parts]
    return v

def parse_yaml_min(path: Path):
    # Minimal YAML subset: maps + nested by 2-space indentation + [a,b] lists
    lines = path.read_text(encoding="utf-8").splitlines()
    stack = [{}]
    indents = [0]
    for raw in lines:
        line = raw.split("#",1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError("Indentation must be multiples of 2 spaces")
        keyval = line.strip()
        if ":" in keyval:
            key, rest = keyval.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            # adjust stack based on indent
            while indent < indents[-1]:
                stack.pop(); indents.pop()
            if indent > indents[-1]:
                # new child dict level
                child = {}
                # attach this child to previous key? Only if last item was a key with empty value
                # But since we hit a new key at deeper indent, we assume previous line created the parent.
                # To handle typical YAML, we need to attach to last inserted key of the current dict.
                # We'll track last_key on each dict via a hidden key "__last_key__".
                raise ValueError("Malformed YAML: unexpected indentation. Ensure parent key has no value and is followed by indented keys.")
            current = stack[-1]
            if rest == "":
                # key with nested mapping to follow
                if key in current and isinstance(current[key], dict):
                    # reuse
                    pass
                else:
                    current[key] = {}
                stack.append(current[key]); indents.append(indent+2)
            else:
                current[key] = parse_scalar(rest)
                current["__last_key__"] = key
        else:
            raise ValueError("Line must contain ':' separating key and value")
    # cleanup helper keys
    def cleanup(d):
        if isinstance(d, dict):
            d.pop("__last_key__", None)
            for k in list(d.keys()):
                d[k] = cleanup(d[k])
        elif isinstance(d, list):
            return [cleanup(x) for x in d]
        return d
    return cleanup(stack[0])

def load_config(path: Path):
    data = parse_yaml_min(path)
    cfg = {
        "input": data.get("input", "sibelius/Hoeren_1.musicxml"),
        "outdir": data.get("outdir", "OUT"),
        "seed": data.get("seed", 42),
        "scales": {
            "section": data.get("scales", {}).get("section", "Tonleiter"),
            "accidentals": ",".join(data.get("scales", {}).get("accidentals", ["sharp","flat","natural"])) if isinstance(data.get("scales", {}).get("accidentals"), list) else data.get("scales", {}).get("accidentals", "sharp,flat,natural"),
            "placeholders": ",".join(data.get("scales", {}).get("placeholders", ["E4","E5"])) if isinstance(data.get("scales", {}).get("placeholders"), list) else data.get("scales", {}).get("placeholders", "E4,E5"),
        },
        "intervals": {
            "section": data.get("intervals", {}).get("section", "Intervalle"),
            "intervals": ",".join(data.get("intervals", {}).get("set", ["m2","M2","m3","M3","P4","TT","P5","m6","M6","m7","M7","P8"])) if isinstance(data.get("intervals", {}).get("set"), list) else data.get("intervals", {}).get("set", "m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8"),
            "direction": data.get("intervals", {}).get("direction", "both"),
        },
        "chords": {
            "section": data.get("chords", {}).get("section", "Akkord"),
            "triads": ",".join(data.get("chords", {}).get("triads", ["maj","min","dim"])) if isinstance(data.get("chords", {}).get("triads"), list) else data.get("chords", {}).get("triads", "maj,min,dim"),
            "inversion": data.get("chords", {}).get("inversion", "random"),
        },
        "rhythms": {
            "section": data.get("rhythms", {}).get("section", "Rhythmus"),
            "note_prob": data.get("rhythms", {}).get("note_prob", 0.7),
        },
        "what": data.get("what", "all"),
    }
    return cfg

def main():
    ap = argparse.ArgumentParser(description="Übungsblatt CLI (with YAML config)")
    ap.add_argument("--config", help="Path to YAML config")
    # Allow overrides from CLI (optional)
    ap.add_argument("--input"); ap.add_argument("--outdir"); ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    if args.config:
        cfg = load_config(Path(args.config))
    else:
        # fallback minimal defaults
        cfg = {
            "input": "sibelius/Hoeren_1.musicxml",
            "outdir": "OUT",
            "seed": 42,
            "scales": {"section":"Tonleiter","accidentals":"sharp,flat,natural","placeholders":"E4,E5"},
            "intervals": {"section":"Intervalle","intervals":"m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8","direction":"both"},
            "chords": {"section":"Akkord","triads":"maj,min,dim","inversion":"random"},
            "rhythms": {"section":"Rhythmus","note_prob":0.7},
            "what": "all",
        }

    # CLI overrides
    if args.input: cfg["input"] = args.input
    if args.outdir: cfg["outdir"] = args.outdir
    if args.seed is not None: cfg["seed"] = args.seed

    inp = Path(cfg["input"]).resolve()
    outdir = Path(cfg["outdir"]).resolve(); outdir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg["seed"])

    what = cfg.get("what","all")
    if what in ("all","scales"):
        run([sys.executable, HERE / "generate_scales.py",
             "--input", inp, "--output", outdir / "Hoeren_1_scales.musicxml",
             "--section-keyword", cfg["scales"]["section"],
             "--accidentals", cfg["scales"]["accidentals"],
             "--placeholders", cfg["scales"]["placeholders"],
             "--seed", seed + 1])

    if what in ("all","intervals"):
        run([sys.executable, HERE / "generate_intervals.py",
             "--input", inp, "--output", outdir / "Hoeren_1_intervals.musicxml",
             "--section-keyword", cfg["intervals"]["section"],
             "--intervals", cfg["intervals"]["intervals"],
             "--direction", cfg["intervals"]["direction"],
             "--seed", seed + 2])

    if what in ("all","chords"):
        run([sys.executable, HERE / "generate_chords.py",
             "--input", inp, "--output", outdir / "Hoeren_1_chords.musicxml",
             "--section-keyword", cfg["chords"]["section"],
             "--triads", cfg["chords"]["triads"],
             "--inversion", cfg["chords"]["inversion"],
             "--seed", seed + 3])

    if what in ("all","rhythms"):
        run([sys.executable, HERE / "generate_rhythms.py",
             "--input", inp, "--output", outdir / "Hoeren_1_rhythms.musicxml",
             "--section-keyword", cfg["rhythms"]["section"],
             "--note-prob", cfg["rhythms"]["note_prob"],
             "--seed", seed + 4])

    print(f"Done. Files saved to {outdir}")

if __name__ == "__main__":
    main()
