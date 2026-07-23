#!/usr/bin/env python3
"""Third baseline condition: SOSA-SHACL after asserting each punned CMPO
parameter class as a sosa:ObservableProperty individual (one triple per class),
the fix Section 6.3 names as planned. Same RNG protocol as the other runs."""
import json, sys, time
import importlib.util
spec = importlib.util.spec_from_file_location("ev", "evaluate_v2.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
import os as _os
def _find(*cands):
    for c in cands:
        if _os.path.exists(c): return c
    raise FileNotFoundError("none of: " + ", ".join(cands))

from pyshacl import validate
from rdflib import Graph, RDF, RDFS, URIRef, Namespace
import rdflib as _r
SH = _r.Namespace("http://www.w3.org/ns/shacl#")
SOSA = ev.SOSA; CMPO = ev.CMPO

def run_val_v(data, shapes):
    conforms, _, rt = validate(data, shacl_graph=shapes, inference="none")
    n = rt.count("Constraint Violation")
    res = set()
    for block in rt.split("Constraint Violation in ")[1:]:
        comp = block.split(" ")[0]; fn = path = val = ""
        for line in block.split("\n"):
            if "Focus Node:" in line: fn = line.split("Focus Node:")[1].strip()
            if "Result Path:" in line: path = line.split("Result Path:")[1].strip()
            if "Value Node:" in line: val = line.split("Value Node:")[1].strip()
        res.add((fn, path, comp, val))
    return n, res

ont = Graph(); ont.parse(_find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl"), format="turtle")
kg = Graph(); kg.parse(_find("kg/kg_cmpo_v2.0.2.ttl", "kg_cmpo_v202.ttl"), format="turtle")
shapes = Graph(); shapes.parse(_find("KWG-SHACL/shacl_sosa.ttl", "shapes/shacl_sosa_external.ttl"  # git clone https://github.com/KnowWhereGraph/KWG-SHACL), format="turtle")
repairs = 0
for shape, pnode in list(shapes.subject_objects(SH.property)):
    if (pnode, SH.path, None) not in shapes:
        orlist = list(shapes.objects(pnode, SH["or"]))
        if orlist:
            shapes.remove((shape, SH.property, pnode))
            for o in orlist:
                shapes.remove((pnode, SH["or"], o)); shapes.add((shape, SH["or"], o))
            repairs += 1
print("repairs:", repairs, flush=True)

sub = ev.build_subgraph(kg, ont)
print("subgraph:", len(sub), flush=True)
# THE FIX: every class under cmpo:CMPParameter asserted as sosa:ObservableProperty individual
punned = set()
for c in ont.transitive_subjects(RDFS.subClassOf, CMPO.CMPParameter):
    if isinstance(c, URIRef):
        sub.add((c, RDF.type, SOSA.ObservableProperty)); punned.add(c)
print("punning-fix triples added:", len(punned), flush=True)

nC, base = run_val_v(sub, shapes)
print("clean baseline AFTER punning fix:", nC, "violations (was 8045)", flush=True)
out = {"clean_after_fix": nC, "punned_classes_typed": len(punned)}
for op in ["T1_missing_value","T2_datatype","T3_negative_value","T4_dangling_foi",
           "T5_plausible_swap","T6_undeclared_property","T7_unit_scale","T8_duplicate_wafer"]:
    undo, seeded = ev.seed(sub, op)
    _, res = run_val_v(sub, shapes)
    new = res - base
    names = [str(s).rsplit('#',1)[-1] for s in seeded]
    strict = sum(1 for nm in names if any(nm in fn for fn,_,_,_ in new))
    removed, added = undo
    for t in added: Graph.remove(sub, t)
    for t in removed: Graph.add(sub, t)
    out[op] = {"seeded": len(seeded), "strict": strict, "new_results": len(new)}
    print(op, out[op], flush=True)
json.dump(out, open("baseline_punningfix_results.json","w"), indent=2)
print("done", flush=True)
