#!/usr/bin/env python3
"""External-baseline study: SOSA-SHACL (Zhu et al., IJCKG 2021; KWG-SHACL repo)
run against the same E2 seeded-error protocol as the paper's tier-1/tier-2 gate.

Two configurations:
  A "as published": shapes on the raw subgraph (instances typed with CMPO
    subclasses only) -- class-targeted shapes are expected to be vacuous.
  B "subclass types materialized": rdf:type closure over rdfs:subClassOf*
    added to the data graph, the remedy the paper's E0/discussion names.

Detection criteria per seeded node, differential vs. the clean baseline:
  strict  = a new (focus,path,component) whose focus contains the node's local name
            (identical to the harness criterion)
  generous= strict OR the node's local name appears in a new violation's value node
Also logs per-config clean-baseline violation counts.
"""
import json, sys, time
import os as _os
def _find(*cands):
    for c in cands:
        if _os.path.exists(c): return c
    raise FileNotFoundError("none of: " + ", ".join(cands) + " -- run from the repository root")

import importlib.util
spec = importlib.util.spec_from_file_location("ev", _find("modpipe/evaluate_v2.py", "evaluate_v2.py"))
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)

from pyshacl import validate
from rdflib import Graph, RDF, RDFS, URIRef

CMPO = ev.CMPO

def run_val_v(data, shapes):
    conforms, _, rt = validate(data, shacl_graph=shapes, inference="none")
    n = rt.count("Constraint Violation")
    res = set()
    for block in rt.split("Constraint Violation in ")[1:]:
        comp = block.split(" ")[0]
        fn, path, val = "", "", ""
        for line in block.split("\n"):
            if "Focus Node:" in line: fn = line.split("Focus Node:")[1].strip()
            if "Result Path:" in line: path = line.split("Result Path:")[1].strip()
            if "Value Node:" in line: val = line.split("Value Node:")[1].strip()
        res.add((fn, path, comp, val))
    return n, res

def type_closure(g, ont):
    """rdf:type materialization over rdfs:subClassOf* (named classes)."""
    supers = {}
    def sup(c):
        if c in supers: return supers[c]
        out = set()
        stack = [c]
        while stack:
            x = stack.pop()
            for o in ont.objects(x, RDFS.subClassOf):
                if isinstance(o, URIRef) and o not in out:
                    out.add(o); stack.append(o)
        supers[c] = out
        return out
    add = Graph()
    for s, t in g.subject_objects(RDF.type):
        if isinstance(t, URIRef):
            for o in sup(t):
                add.add((s, RDF.type, o))
    return add

def main():
    t0 = time.time()
    ont = Graph(); ont.parse(_find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl"), format="turtle")
    kg = Graph(); kg.parse(_find("kg/kg_cmpo_v2.0.2.ttl", "kg_cmpo_v202.ttl"), format="turtle")
    # SOSA-SHACL suite: git clone https://github.com/KnowWhereGraph/KWG-SHACL in the repo root
    sosa_shapes = Graph(); sosa_shapes.parse(_find("KWG-SHACL/shacl_sosa.ttl", "shapes/shacl_sosa_external.ttl"), format="turtle")
    # Minimal mechanical repair: the published suite wraps four sh:or lists in
    # sh:property blank nodes carrying no sh:path (two each in the observation
    # and actuation node shapes), which strict validators
    # (pySHACL) reject as malformed property shapes. Hoist those sh:or lists
    # to the owning node shape; semantics unchanged.
    SH = ev.rdflib.Namespace("http://www.w3.org/ns/shacl#") if hasattr(ev, "rdflib") else None
    import rdflib as _r
    SH = _r.Namespace("http://www.w3.org/ns/shacl#")
    repairs = 0
    for shape, pnode in list(sosa_shapes.subject_objects(SH.property)):
        if (pnode, SH.path, None) not in sosa_shapes:
            orlist = list(sosa_shapes.objects(pnode, SH["or"]))
            if orlist:
                sosa_shapes.remove((shape, SH.property, pnode))
                for o in orlist:
                    sosa_shapes.remove((pnode, SH["or"], o))
                    sosa_shapes.add((shape, SH["or"], o))
                for t in list(sosa_shapes.predicate_objects(pnode)):
                    sosa_shapes.remove((pnode, t[0], t[1]))
                repairs += 1
    print(f"repaired {repairs} malformed pathless sh:property wrappers", flush=True)
    core = Graph(); core.parse(_find("shapes/shapes_core.ttl", "shapes_core.ttl"), format="turtle")
    print(f"loaded: kg={len(kg)} ont={len(ont)} sosa-shapes={len(sosa_shapes)}", flush=True)

    sub = ev.build_subgraph(kg, ont)          # same RNG(42) first consumption as harness
    print(f"subgraph: {len(sub)} triples", flush=True)

    inferred = type_closure(sub, ont)
    print(f"materialized type triples: {len(inferred)}", flush=True)

    def matg():
        m = Graph()
        for t in sub: m.add(t)
        for t in inferred: m.add(t)
        return m

    # clean baselines
    base = {}
    nA, rA = run_val_v(sub, sosa_shapes);   base["A"] = rA
    print(f"baseline A (as published): {nA} violations", flush=True)
    nB, rB = run_val_v(matg(), sosa_shapes); base["B"] = rB
    print(f"baseline B (types materialized): {nB} violations", flush=True)
    # harness tiers for consistency check
    _, n1, f1 = ev.run_val(sub, core)
    _, f2 = ev.tier2_audit(sub)
    base["tier1"] = f1
    base["tier12"] = f1 | f2
    print(f"baseline tier1={n1}", flush=True)

    OPS = ["T1_missing_value", "T2_datatype", "T3_negative_value", "T4_dangling_foi",
           "T5_plausible_swap", "T6_undeclared_property", "T7_unit_scale", "T8_duplicate_wafer"]
    out = {"baseline_violations": {"A": nA, "B": nB}}
    for op in OPS:
        undo, seeded = ev.seed(sub, op)
        row = {"seeded": len(seeded)}
        # config A
        _, resA = run_val_v(sub, sosa_shapes)
        newA = resA - base["A"]
        # config B
        _, resB = run_val_v(matg(), sosa_shapes)
        newB = resB - base["B"]
        for lbl, new in [("A", newA), ("B", newB)]:
            names = [str(s).rsplit('#', 1)[-1] for s in seeded]
            strict = sum(1 for nm in names if any(nm in fn for fn, _, _, _ in new))
            gen = sum(1 for nm in names if any(nm in fn or nm in val for fn, _, _, val in new))
            row[f"sosa_{lbl}_strict"] = strict
            row[f"sosa_{lbl}_generous"] = gen
            row[f"sosa_{lbl}_new_results"] = len(new)
        # harness tiers on same mutation (consistency with Table 1)
        _, _, ff1 = ev.run_val(sub, core)
        _, ff2 = ev.tier2_audit(sub)
        for lbl, focus in [("tier1", ff1), ("tier12", ff1 | ff2)]:
            new = focus - base[lbl]
            det = sum(1 for s in seeded if any(str(s).rsplit('#', 1)[-1] in fn for fn, _, _ in new))
            row[lbl] = det
        removed, added = undo
        for t in added: Graph.remove(sub, t)
        for t in removed: Graph.add(sub, t)
        out[op] = row
        print(f"{op}: {row}", flush=True)
    out["runtime_s"] = round(time.time() - t0, 1)
    json.dump(out, open("baseline_sosashacl_results.json", "w"), indent=2)
    print(f"done in {out['runtime_s']}s", flush=True)

if __name__ == "__main__":
    main()
