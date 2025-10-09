
import xml.etree.ElementTree as ET
from typing import List, Tuple

SEMITONES = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
def pitch_to_midi(step:str, alter:int, octave:int)->int:
    return (octave+1)*12 + SEMITONES[step] + (alter or 0)
def midi_to_pitch(midi:int)->Tuple[str,int,int]:
    octave = midi//12 - 1
    pc = midi % 12
    choices = {0:("C",0),1:("C",1),2:("D",0),3:("D",1),4:("E",0),5:("F",0),6:("F",1),7:("G",0),8:("G",1),9:("A",0),10:("A",1),11:("B",0)}
    step, alter = choices[pc]; return step, alter, octave
INTERVAL_TO_SEMITONES = {"m2":1,"M2":2,"m3":3,"M3":4,"P4":5,"TT":6,"P5":7,"m6":8,"M6":9,"m7":10,"M7":11,"P8":12}
def find_sections_by_words(root:ET.Element):
    sections = []; parts = root.findall("part")
    for pi, part in enumerate(parts):
        for mi, meas in enumerate(part.findall("measure")):
            for d in meas.findall("direction"):
                for w in d.findall(".//words"):
                    if w.text and w.text.strip(): sections.append((w.text.strip(), pi, mi))
    return sections
def get_measures_for_section(root:ET.Element, keyword:str)->List[ET.Element]:
    parts = root.findall("part"); sections = find_sections_by_words(root); target=None
    for label, pi, mi in sections:
        if keyword.lower() in label.lower(): target=(pi,mi,label); break
    if target is None: return []
    pi, start_mi, _ = target
    following_idx=None
    for label2, pi2, mi2 in sections:
        if pi2==pi and mi2>start_mi: following_idx=mi2; break
    measures = parts[pi].findall("measure")
    return measures[start_mi:] if following_idx is None else measures[start_mi:following_idx]
def first_n_notes_in_measure(measure:ET.Element, n:int=2):
    out=[]; 
    for note in measure.findall("note"):
        if note.find("rest") is not None: continue
        out.append(note)
        if len(out)>=n: break
    return out
def note_pitch(note:ET.Element):
    p = note.find("pitch"); 
    if p is None: return None
    step = p.findtext("step"); alt_t = p.findtext("alter")
    alter = int(alt_t) if alt_t is not None and alt_t.strip()!="" else 0
    octave = int(p.findtext("octave"))
    return step, alter, octave
def set_note_pitch(note:ET.Element, step:str, alter:int, octave:int):
    p = note.find("pitch")
    if p is None:
        p = ET.SubElement(note, "pitch")
        r = note.find("rest")
        if r is not None: note.remove(r)
    step_el = p.find("step"); step_el = step_el or ET.SubElement(p,"step"); step_el.text = step
    alter_el = p.find("alter")
    if alter in (0,None):
        if alter_el is not None: p.remove(alter_el)
    else:
        alter_el = alter_el or ET.SubElement(p,"alter"); alter_el.text = str(int(alter))
    octave_el = p.find("octave"); octave_el = octave_el or ET.SubElement(p,"octave"); octave_el.text = str(int(octave))
def clone_note_as_chord_tone(root_note:ET.Element)->ET.Element:
    new_note = ET.Element("note")
    ET.SubElement(new_note, "chord")
    for tag in ("duration","voice","type","stem","staff","time-modification","dot","notations"):
        el = root_note.find(tag)
        if el is not None:
            def cp(e):
                x = ET.Element(e.tag, e.attrib)
                x.text = e.text
                for c in e:
                    x.append(cp(c))
                return x
            new_note.append(cp(el))
    return new_note
def write_tree(tree:ET.ElementTree, path:str):
    tree.write(path, encoding="utf-8", xml_declaration=True)
