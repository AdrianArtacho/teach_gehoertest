#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # pip install pyyaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

HERE = Path(__file__).resolve().parent

def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)

def load_cfg(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data

def apply_profile(cfg: dict, profile_name: str | None) -> dict:
    if not profile_name:
        return cfg
    profs = cfg.get("profiles") or {}
    prof = profs.get(profile_name)
    if not prof:
        return cfg
    merged = dict(cfg)
    for k, v in prof.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            nv = dict(merged[k])
            nv.update(v)
            merged[k] = nv
        else:
            merged[k] = v
    return merged

def main():
    ap = argparse.ArgumentParser(description="Übungsblatt generator (PyYAML edition).")
    ap.add_argument("--config", required=True, help="Path to YAML config")
    ap.add_argument("--profile", default=None, help="Optional profile name to apply (also embedded into titles)")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_cfg(cfg_path)
    cfg = apply_profile(cfg, args.profile)

    outdir = Path(cfg.get("outdir", "OUT"))
    outdir.mkdir(parents=True, exist_ok=True)

    # CLEANUP: remove existing MusicXML files before generation
    for pattern in ("*.musicxml", "*.music.xml"):
        for _f in outdir.glob(pattern):
            try:
                _f.unlink()
            except Exception:
                pass

    inputs = cfg.get("inputs", {}) or {}
    seed = cfg.get("seed")

    # ---------------- SCALES ----------------
    scales_in = inputs.get("scales")
    if scales_in:
        scales_out = outdir / "Hoeren_scales.musicxml"
        cmd = [sys.executable, HERE / "generate_scales.py",
               "--input", scales_in, "--output", scales_out]
        s_cfg = cfg.get("scales", {}) or {}
        if "accidental_tags" in s_cfg:
            cmd += ["--accidental-tags", ",".join(s_cfg["accidental_tags"])]
        elif "accidentals" in s_cfg:
            cmd += ["--accidentals", ",".join(s_cfg["accidentals"])]
        if "placeholders" in s_cfg:
            cmd += ["--placeholders", ",".join(s_cfg["placeholders"])]
        if "alter_count" in s_cfg:
            cmd += ["--alter-count", str(s_cfg["alter_count"])]
        if "alter_ratio" in s_cfg:
            cmd += ["--alter-ratio", str(s_cfg["alter_ratio"])]
        if "hide_articulations" in s_cfg:
            cmd += ["--hide-articulations", str(s_cfg["hide_articulations"]).lower()]
        if "target_voice" in s_cfg:
            cmd += ["--target-voice", str(s_cfg["target_voice"])]
        if "target_staff" in s_cfg:
            cmd += ["--target-staff", str(s_cfg["target_staff"])]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        if args.profile:
            cmd += ["--profile-name", args.profile]
        run(cmd)

        # Arbeitsblatt for scales
        run([sys.executable, HERE / "make_arbeitsblatt.py",
             "--mode", "scales",
             "--action", (cfg.get("worksheet", {}) or {}).get("scales", "hide"),
             "--input", scales_out,
             "--output", outdir / "Hoeren_scales_arbeitsblatt.musicxml"])

    # ---------------- INTERVALS ----------------
    intervals_in = inputs.get("intervals")
    if intervals_in:
        intervals_out = outdir / "Hoeren_intervals.musicxml"
        cmd = [sys.executable, HERE / "generate_intervals.py",
               "--input", intervals_in, "--output", intervals_out]
        i_cfg = cfg.get("intervals", {}) or {}
        if "set" in i_cfg:
            cmd += ["--set", ",".join(i_cfg["set"])]
        if "direction" in i_cfg:
            cmd += ["--direction", i_cfg["direction"]]
        if "accidental_tags" in i_cfg:
            cmd += ["--accidental-tags", ",".join(i_cfg["accidental_tags"])]  # second-note filter
        pos_tag = i_cfg.get("position_tag") or i_cfg.get("position")
        if pos_tag:
            cmd += ["--position-tag", str(pos_tag).strip().lower()]
        if seed is not None:
            cmd += ["--seed", str(seed)]
        if args.profile:
            cmd += ["--profile-name", args.profile]  # put profile label into <work-title> and <credit-words>
        run(cmd)

        # Arbeitsblatt for intervals
        run([sys.executable, HERE / "make_arbeitsblatt.py",
             "--mode", "intervals",
             "--action", (cfg.get("worksheet", {}) or {}).get("intervals", "hide"),
             "--input", intervals_out,
             "--output", outdir / "Hoeren_intervals_arbeitsblatt.musicxml"])

    # ---------------- CHORDS ----------------
    chords_in = inputs.get("chords")
    if chords_in:
        chords_out = outdir / "Hoeren_chords.musicxml"
        cmd = [sys.executable, HERE / "generate_chords.py",
               "--input", chords_in, "--output", chords_out]
        c_cfg = cfg.get("chords", {}) or {}
        if seed is not None:
            cmd += ["--seed", str(seed)]
        run(cmd)

        run([sys.executable, HERE / "make_arbeitsblatt.py",
             "--mode", "chords",
             "--action", (cfg.get("worksheet", {}) or {}).get("chords", "hide"),
             "--input", chords_out,
             "--output", outdir / "Hoeren_chords_arbeitsblatt.musicxml"])

    # ---------------- RHYTHMS ----------------
    rhythms_in = inputs.get("rhythms")
    if rhythms_in:
        rhythms_out = outdir / "Hoeren_rhythm.musicxml"
        cmd = [sys.executable, HERE / "generate_rhythms.py",
               "--input", rhythms_in, "--output", rhythms_out]
        r_cfg = cfg.get("rhythms", {}) or {}
        if seed is not None:
            cmd += ["--seed", str(seed)]
        run(cmd)

        run([sys.executable, HERE / "make_arbeitsblatt.py",
             "--mode", "rhythms",
             "--action", (cfg.get("worksheet", {}) or {}).get("rhythms", "hide"),
             "--input", rhythms_out,
             "--output", outdir / "Hoeren_rhythm_arbeitsblatt.musicxml"])

    print(f"Done. Files saved to {outdir}")

if __name__ == "__main__":
    main()
