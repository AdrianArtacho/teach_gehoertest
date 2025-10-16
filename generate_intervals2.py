#!/usr/bin/env python3
import argparse
import random
import xml.etree.ElementTree as ET

STEP_TO_INDEX = {'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}
INDEX_TO_STEP = {v:k for k,v in STEP_TO_INDEX.items()}
NAT_SEMITONES = [0,2,4,5,7,9,11]

INTERVAL_TABLE = {
    'm2': (1,1), 'M2': (1,2),
    'm3': (2,3), 'M3': (2,4),
    'P4': (3,5), 'TT': (4,6),
    'P5': (4,7),
    'm6': (5,8), 'M6': (5,9),
    'm7': (6,10), 'M7': (6,11),
    'P8': (7,12),
}

def parse_csv_list(s):
    if not s: return []
    return [t.strip() for t in s.split(',') if t.strip()]

def note_is_pitched(note):
    return note.find('pitch') is not None

def get_pitch(note):
    p = note.find('pitch')
    if p is None: return None
    step = (p.findtext('step') or '').upper()
    octave = p.findtext('octave')
    if not step or octave is None: return None
    octave = int(octave)
    alt_el = p.find('alter')
    alter = int(float(alt_el.text)) if alt_el is not None and (alt_el.text or '').strip() != '' else 0
    return step, octave, alter

def set_pitch(note, step, octave, alter):
    p = note.find('pitch')
    if p is None:
        p = ET.SubElement(note, 'pitch')
    st = p.find('step');   st = st if st is not None else ET.SubElement(p, 'step');   st.text = step
    oc = p.find('octave'); oc = oc if oc is not None else ET.SubElement(p, 'octave'); oc.text = str(int(octave))
    al = p.find('alter');  al = al if al is not None else ET.SubElement(p, 'alter');  al.text = str(int(alter))

def clear_explicit_accidental(note):
    for acc in list(note.findall('accidental')):
        note.remove(acc)

def midi_of(step, octave, alter):
    step_idx = STEP_TO_INDEX[step]
    base = NAT_SEMITONES[step_idx] + 12 * (octave + 1)
    return base + alter

def diatonic_advance(step, octave, diatonic_steps, direction):
    sidx = STEP_TO_INDEX[step]
    if direction == 'down':
        diatonic_steps = -diatonic_steps
    new_idx = sidx + diatonic_steps
    wraps, mod = divmod(new_idx, 7)
    if new_idx < 0 and mod != 0:
        wraps -= 1
    new_step_idx = new_idx % 7
    new_step = INDEX_TO_STEP[new_step_idx]
    new_oct = octave + wraps
    return new_step, new_oct

def required_alter_for_interval(base_step, base_oct, base_alter, ivl_name, direction):
    d_steps, semis = INTERVAL_TABLE[ivl_name]
    if direction == 'down':
        semis = -semis
    base_midi = midi_of(base_step, base_oct, base_alter)
    target_midi = base_midi + semis
    tgt_step, tgt_oct = diatonic_advance(base_step, base_oct, d_steps, direction)
    natural_midi = midi_of(tgt_step, tgt_oct, 0)
    alter = target_midi - natural_midi
    if alter < -2 or alter > 2:
        return None, None, None
    return tgt_step, tgt_oct, int(alter)

def duration_val(note):
    d = note.findtext('duration')
    try:
        return int(d) if d is not None else None
    except Exception:
        return None

def note_type(note):
    return (note.findtext('type') or '').strip().lower()

def staff_num(note):
    s = note.findtext('staff')
    try:
        return int(s) if s is not None else 1
    except Exception:
        return 1

def voice_id(note):
    v = note.findtext('voice')
    return v.strip() if v else '1'

def collect_events_by_measure(part):
    measures = []
    for meas in part.findall('measure'):
        events = []
        time = 0
        for el in list(meas):
            tag = el.tag
            if tag == 'note':
                d = duration_val(el) or 0
                ev = {
                    'note': el,
                    'onset': time,
                    'dur': d,
                    'type': note_type(el),
                    'voice': voice_id(el),
                    'staff': staff_num(el),
                    'pitch': get_pitch(el) if note_is_pitched(el) else None
                }
                events.append(ev)
                time += d
            elif tag == 'forward':
                d = el.findtext('duration')
                try:
                    time += int(d) if d is not None else 0
                except Exception:
                    pass
            elif tag == 'backup':
                d = el.findtext('duration')
                try:
                    time -= int(d) if d is not None else 0
                except Exception:
                    pass
        measures.append(events)
    return measures

def pair_whole_with_quarter(measure_events):
    pairs = []
    by_onset = {}
    for ev in measure_events:
        by_onset.setdefault(ev['onset'], []).append(ev)
    onsets = sorted(by_onset.keys())
    for t in onsets:
        group = by_onset[t]
        bases = [e for e in group if e['type'] == 'whole' and e['pitch']]
        targets = [e for e in group if e['type'] == 'quarter' and e['pitch']]
        for b in bases:
            cand = None
            for tgt in targets:
                if tgt['voice'] != b['voice']:
                    cand = tgt
                    break
            if cand is None:
                for t2 in onsets:
                    if t2 > t:
                        for ev2 in by_onset[t2]:
                            if ev2['type'] == 'quarter' and ev2['pitch'] and ev2['voice'] != b['voice']:
                                cand = ev2
                                break
                    if cand: break
            if cand is not None:
                pairs.append((b, cand))
    return pairs

def main():
    ap = argparse.ArgumentParser(description='Intervals: tag-aware, multi-voice pairing (WHOLE base + QUARTER target).')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--set', default='m2,M2,m3,M3,P4,TT,P5,m6,M6,m7,M7,P8')
    ap.add_argument('--direction', default='both', choices=['up','down','both'])
    ap.add_argument('--position-tag', default='up', choices=['up','down','auto'],
                help='Force 2nd note above/below base (default: up)')
    ap.add_argument('--accidental-tags', default='')
    ap.add_argument('--resample-attempts', type=int, default=50)
    ap.add_argument('--require-tag-match', type=str, default='true')
    ap.add_argument('--seed', type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    interval_set = [s for s in parse_csv_list(args.set) if s in INTERVAL_TABLE]
    if not interval_set:
        interval_set = ['M2','m2','M3','m3','P4','TT','P5','M6','m6','M7','m7','P8']
    tags = parse_csv_list(args.accidental_tags)
    allowed_alters = [0,1,-1] if not tags else [a for a in (0,1,-1)
                                                if (a==0 and 'natural' in tags) or
                                                   (a==1 and 'sharp' in tags) or
                                                   (a==-1 and 'flat' in tags)]
    require_match = (str(args.require_tag_match).strip().lower() in ('1','true','yes','y'))
    directions = ['up','down'] if args.direction == 'both' else [args.direction]
    if args.position_tag in ('up','down'):
        directions = [args.position_tag]

    tree = ET.parse(args.input); root = tree.getroot()

    changed = 0
    for part in root.findall('part'):
        measures = collect_events_by_measure(part)
        for evs in measures:
            pairs = pair_whole_with_quarter(evs)
            for base_ev, tgt_ev in pairs:
                base_step, base_oct, base_alt = base_ev['pitch']
                candidates = [(ivl, d) for ivl in interval_set for d in directions]
                random.shuffle(candidates)
                chosen = None; tries = 0
                while candidates and tries < args.resample_attempts:
                    ivl, direc = candidates.pop(); tries += 1
                    tgt = required_alter_for_interval(base_step, base_oct, base_alt, ivl, direc)
                    if tgt == (None, None, None):
                        continue
                    tgt_step, tgt_oct, tgt_alter = tgt
                    if tgt_alter in allowed_alters:
                        chosen = (tgt_step, tgt_oct, tgt_alter); break
                if chosen is None and not require_match:
                    for ivl in interval_set:
                        for direc in directions:
                            tgt = required_alter_for_interval(base_step, base_oct, base_alt, ivl, direc)
                            if tgt != (None, None, None):
                                chosen = tgt; break
                        if chosen: break
                if chosen is not None:
                    step, octv, alt = chosen
                    set_pitch(tgt_ev['note'], step, octv, alt)
                    clear_explicit_accidental(tgt_ev['note'])
                    changed += 1

    tree.write(args.output, encoding='utf-8', xml_declaration=True)
    print(f'Intervals: wrote {args.output}; changed {changed} targets with tag-compliant accidentals.')

# simple csv parser (duplicated intentionally to keep it local)
def parse_csv_list(s):
    if not s: return []
    return [t.strip() for t in s.split(',') if t.strip()]

if __name__ == '__main__':
    main()
