#!/usr/bin/env python3
"""Automatic, human-free evaluation harness for the CMPO knowledge graph.

Runs three experiments against the shipped artifacts of the KGPortal repo:

  E1  Conformance audit: validate the shipped instance graph against the
      shipped v1 shapes and the revised v2 shapes, before and after RDFS
      subclass materialisation. Also reports oracle-vacuity statistics
      (shapes whose target class matches no node, shapes whose property
      path never occurs in the data).

  E2  Seeded-error study (mutation testing): mechanically inject errors
      from an externally grounded taxonomy of data-quality error classes
      into the instance graph, and measure per-class detection by the v1
      and v2 shape suites.

  E3  Competency-question suite: execute literature-derived competency
      questions as SPARQL against the (materialised) instance graph and
      report the answerability funnel.

Every number printed by this script is computed from the artifacts in
this repository; nothing is estimated or interpolated. Seeding uses a
fixed RNG seed for reproducibility.
"""
import json
import random
import re
import time
from collections import Counter

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

CMPO = Namespace("https://tucid/cpmo/")
INST = Namespace("https://tucid/cpmo/instance/")
SH = Namespace("http://www.w3.org/ns/shacl#")
RNG = random.Random(42)

RESULTS = {}


def load():
    ont = Graph(); ont.parse("ontology/Schema.ttl", format="turtle")
    data = Graph(); data.parse("ontology/Instances.ttl", format="turtle")
    v1 = Graph(); v1.parse("SHACL/cmpo_shapes.ttl", format="turtle")
    v2 = Graph(); v2.parse("evaluation/cmpo_shapes_v2.ttl", format="turtle")
    return ont, data, v1, v2


def subclass_closure(ont):
    sub = {}
    for s, o in ont.subject_objects(RDFS.subClassOf):
        if isinstance(o, URIRef):
            sub.setdefault(s, set()).add(o)

    def ancestors(c, seen=None):
        seen = seen if seen is not None else set()
        for p in sub.get(c, ()):
            if p not in seen:
                seen.add(p)
                ancestors(p, seen)
        return seen

    return ancestors


def materialise(data, ancestors):
    g = Graph()
    for t in data:
        g.add(t)
    for s, o in list(data.subject_objects(RDF.type)):
        for a in ancestors(o):
            g.add((s, RDF.type, a))
    return g


def run_validation(data, shapes, ont):
    conforms, _, rt = validate(data, shacl_graph=shapes, ont_graph=ont,
                               inference="none")
    n = rt.count("Constraint Violation")
    focus = set()
    for block in rt.split("Constraint Violation in ")[1:]:
        comp = block.split(" ")[0]
        fn, path = "", ""
        for line in block.split("\n"):
            if "Focus Node:" in line: fn = line.split("Focus Node:")[1].strip()
            if "Result Path:" in line: path = line.split("Result Path:")[1].strip()
        focus.add((fn, path, comp))
    paths = Counter()
    for block in rt.split("Constraint Violation in ")[1:]:
        comp = block.split(" ")[0]
        path = ""
        for line in block.split("\n"):
            if "Result Path:" in line:
                path = line.split("Result Path:")[1].strip()
        paths[(comp, path)] += 1
    return conforms, n, focus, dict((f"{c}|{p}", v) for (c, p), v in paths.items())


def experiment_1(ont, data, datam, v1, v2):
    print("== E1: conformance audit ==")
    out = {}
    out["graph_stats"] = {
        "schema_triples": len(ont),
        "instance_triples": len(data),
        "typed_instances": len(set(data.subjects(RDF.type, None))),
        "runs": len(set(data.subjects(RDF.type, CMPO.Measurement))),
    }
    for label, shapes in [("v1", v1), ("v2", v2)]:
        for regime, d in [("asserted", data), ("materialised", datam)]:
            if label == "v2" and regime == "asserted":
                continue
            conforms, n, focus, paths = run_validation(d, shapes, ont)
            out[f"{label}_{regime}"] = {"conforms": conforms, "violations": n,
                                        "by_constraint": paths}
            print(f"  {label} shapes, {regime} types: {n} violations")
    # vacuity: v1 target classes with zero nodes (asserted) and paths unused
    tviews = {}
    for lbl, shp in [("v1", v1), ("v2", v2)]:
        empty_asserted = []
        for t in set(shp.objects(None, SH.targetClass)):
            if not any(data.subjects(RDF.type, t)):
                empty_asserted.append(str(t))
        tviews[lbl] = sorted(empty_asserted)
    out["targets_with_zero_asserted_instances"] = tviews
    out["rdf_value_triples_in_data"] = len(list(data.subject_objects(RDF.value)))
    # shipped-data quality observations
    wafer_ids = [str(s) for s in data.subjects(RDF.type, CMPO.Wafer)]
    lower_map = Counter(w.lower() for w in wafer_ids)
    out["wafer_nodes"] = len(wafer_ids)
    out["case_variant_wafer_duplicates"] = sum(1 for v in lower_map.values() if v > 1)
    out["literal_executedOn"] = sum(1 for _, o in data.subject_objects(CMPO.executedOn)
                                    if isinstance(o, Literal))
    print(f"  wafer nodes: {out['wafer_nodes']}, case-variant duplicate pairs: "
          f"{out['case_variant_wafer_duplicates']}, literal executedOn: "
          f"{out['literal_executedOn']}")
    return out


# ---------------- E2: seeded-error study ----------------

def pick_params(datam, cls, k):
    nodes = [s for s in datam.subjects(RDF.type, cls)
             if (s, CMPO.hasNumericValue, None) in datam]
    RNG.shuffle(nodes)
    return nodes[:k]


def seed_errors(g, operator, k=50):
    """Mutate g IN PLACE. Return (undo_log, seeded node set).
    undo_log is (removed_triples, added_triples)."""
    seeded = set()
    removed, added = [], []
    _orig_remove, _orig_add = g.remove, g.add
    def rm(t):
        removed.append(t); _orig_remove(t)
    def ad(t):
        added.append(t); _orig_add(t)
    g.remove, g.add = rm, ad
    if operator == "T1_missing_value":
        for s in pick_params(g, CMPO.Parameter, k):
            for o in list(g.objects(s, CMPO.hasNumericValue)):
                g.remove((s, CMPO.hasNumericValue, o))
            seeded.add(s)
    elif operator == "T2_datatype":
        for s in pick_params(g, CMPO.Parameter, k):
            for o in list(g.objects(s, CMPO.hasNumericValue)):
                g.remove((s, CMPO.hasNumericValue, o))
                g.add((s, CMPO.hasNumericValue, Literal("N/A")))
            seeded.add(s)
    elif operator == "T3_negative_value":
        for s in pick_params(g, CMPO.Pressure, k):
            for o in list(g.objects(s, CMPO.hasNumericValue)):
                try:
                    val = abs(float(o))
                except Exception:
                    continue
                g.remove((s, CMPO.hasNumericValue, o))
                g.add((s, CMPO.hasNumericValue,
                       Literal(-(val + 1.0), datatype=XSD.float)))
            seeded.add(s)
    elif operator == "T4_dangling_ref":
        for s in pick_params(g, CMPO.Parameter, k):
            for o in list(g.objects(s, CMPO.isMeasurementOf)):
                g.remove((s, CMPO.isMeasurementOf, o))
            g.add((s, CMPO.isMeasurementOf, Literal("missing_run")))
            seeded.add(s)
    elif operator == "T5_plausible_swap":
        nodes = pick_params(g, CMPO.Pressure, 2 * k)
        for a, b in zip(nodes[:k], nodes[k:2 * k]):
            va = next(iter(g.objects(a, CMPO.hasNumericValue)), None)
            vb = next(iter(g.objects(b, CMPO.hasNumericValue)), None)
            if va is None or vb is None:
                continue
            g.remove((a, CMPO.hasNumericValue, va)); g.add((a, CMPO.hasNumericValue, vb))
            g.remove((b, CMPO.hasNumericValue, vb)); g.add((b, CMPO.hasNumericValue, va))
            seeded.add(a); seeded.add(b)
    elif operator == "T6_unit_label":
        for s in pick_params(g, CMPO.Pressure, k):
            for o in list(g.objects(s, CMPO.hasUnit)):
                g.remove((s, CMPO.hasUnit, o))
            g.add((s, CMPO.hasUnit, Literal("bar")))
            seeded.add(s)
    elif operator == "T7_unit_scale":
        for s in pick_params(g, CMPO.Pressure, k):
            for o in list(g.objects(s, CMPO.hasNumericValue)):
                try:
                    val = float(o)
                except Exception:
                    continue
                g.remove((s, CMPO.hasNumericValue, o))
                g.add((s, CMPO.hasNumericValue,
                       Literal(val * 6.895, datatype=XSD.float)))
            seeded.add(s)
    elif operator == "T8_duplicate_wafer":
        wafers = list(g.subjects(RDF.type, CMPO.Wafer))[:k]
        for w in wafers:
            dup = URIRef(str(w) + "_dup")
            g.add((dup, RDF.type, CMPO.Wafer))
            g.add((dup, CMPO.hasID, Literal(str(w).rsplit("_", 1)[-1])))
            seeded.add(dup)
    g.remove, g.add = _orig_remove, _orig_add
    return (removed, added), seeded


def build_subgraph(datam, n_runs=200):
    """Closed subgraph around the first n_runs runs (plus all non-run-scoped context nodes)."""
    runs = sorted(set(datam.subjects(RDF.type, CMPO.Measurement)), key=str)[:n_runs]
    keep = set(runs)
    g = Graph()
    frontier = list(runs)
    depth = 0
    while frontier and depth < 3:
        nxt = []
        for s in frontier:
            for p, o in datam.predicate_objects(s):
                g.add((s, p, o))
                if isinstance(o, URIRef) and o not in keep:
                    keep.add(o); nxt.append(o)
        frontier = nxt; depth += 1
    # also keep standalone wafers etc. types
    for s in keep:
        for t in datam.objects(s, RDF.type):
            g.add((s, RDF.type, t))
    return g


def experiment_2(ont, datam, v1, v2, baselines_unused):
    print("== E2: seeded-error study (k=50 per class, seed=42, 200-run subgraph) ==")
    sub = build_subgraph(datam)
    print(f"  subgraph: {len(sub)} triples")
    baselines = {}
    for label, shapes in [("v1", v1), ("v2", v2)]:
        _, n0, focus, _ = run_validation(sub, shapes, ont)
        baselines[label] = focus
        print(f"  clean subgraph baseline {label}: {n0} violations")
    operators = ["T1_missing_value", "T2_datatype", "T3_negative_value",
                 "T4_dangling_ref", "T5_plausible_swap", "T6_unit_label",
                 "T7_unit_scale", "T8_duplicate_wafer"]
    out = {}
    for op in operators:
        undo, seeded = seed_errors(sub, op)
        row = {"seeded": len(seeded)}
        for label, shapes in [("v1", v1), ("v2", v2)]:
            _, n, focus, _ = run_validation(sub, shapes, ont)
            base_focus = baselines[label]
            new_focus = focus - base_focus
            # a seeded node is detected iff a NEW (focus, path, component)
            # validation result appears for it relative to the clean baseline
            def local(u):
                u = str(u)
                return u.rsplit('/', 1)[-1]
            detected = sum(1 for s in seeded
                           if any(local(s) in fn for fn, _, _ in new_focus))
            row[label] = {"total_violations": n,
                          "new_focus_nodes": len(new_focus),
                          "seeded_detected": detected}
        out[op] = row
        # revert mutation
        removed, added = undo
        for t in added:
            sub.remove(t)
        for t in removed:
            sub.add(t)
        print(f"  {op}: seeded={row['seeded']} | v1 detected={row['v1']['seeded_detected']}"
              f" | v2 detected={row['v2']['seeded_detected']}")
    return out


# ---------------- E3: competency questions ----------------

CQS = [
    ("CQ1", "Which process parameters were recorded for a given polishing run?",
     "PHM16 dataset documentation (per-run sensor channels)",
     """SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {
        inst:cmp_run_-4224160592_A_00282 cmpo:hasMeasurement ?p . }"""),
    ("CQ2", "What was the average removal rate of a given wafer at each stage?",
     "PHM16 challenge target variable",
     """SELECT ?run ?v WHERE {
        ?run cmpo:hasInput inst:WAFER_-4224160592 ; cmpo:hasMeasurement ?m .
        ?m a cmpo:AverageRemovalRate ; cmpo:hasNumericValue ?v . } LIMIT 5"""),
    ("CQ3", "Which pressure zones of the polishing head were recorded, and with which units?",
     "Multi-zone head pressure control (Luo & Dornfeld 2004, ch. on wafer-scale uniformity)",
     """SELECT DISTINCT ?cls ?u WHERE {
        ?p a ?cls ; cmpo:hasUnit ?u .
        ?cls rdfs:subClassOf+ cmpo:Pressure . } LIMIT 20"""),
    ("CQ4", "What conditioning (dresser) usage accompanied a given run?",
     "Pad conditioning affects removal rate (CMP conditioning literature)",
     """SELECT ?name ?v WHERE {
        ?p cmpo:isMeasurementOf inst:cmp_run_-4224160592_A_00282 ;
           a cmpo:Conditioning ; cmpo:hasParameterName ?name ;
           cmpo:hasNumericValue ?v . } LIMIT 10"""),
    ("CQ5", "Which slurry and recipe were used by each run?",
     "Slurry chemistry / recipe as removal-rate factors (Preston-equation extensions)",
     """SELECT ?run ?s ?r WHERE {
        ?run cmpo:usedSlurry ?s ; cmpo:usesRecipe ?r . } LIMIT 5"""),
    ("CQ6", "Which runs share the same recipe as a given run?",
     "Run-to-run comparability (virtual metrology setting, Winkler et al. 2025)",
     """SELECT (COUNT(DISTINCT ?other) AS ?n) WHERE {
        inst:cmp_run_-4224160592_A_00282 cmpo:usesRecipe ?r .
        ?other cmpo:usesRecipe ?r . }"""),
    ("CQ7", "For which runs is the removal-rate measurement missing?",
     "Completeness check; PHM16 has runs without ground truth",
     """SELECT (COUNT(?run) AS ?n) WHERE {
        ?run a cmpo:Measurement .
        FILTER NOT EXISTS { ?run cmpo:hasMeasurement ?m .
                            ?m a cmpo:AverageRemovalRate . } }"""),
    ("CQ8", "What slurry chemistry parameters (e.g. pH) are recorded, with values?",
     "Slurry chemistry as MRR driver (CMP chemistry literature)",
     """SELECT DISTINCT ?name WHERE {
        ?p a cmpo:SlurryChemistryParameter ; cmpo:hasParameterName ?name . } LIMIT 30"""),
    ("CQ9", "Which chamber was each run executed in?",
     "Chamber as context variable (PHM16 dataset field)",
     """SELECT ?run ?c WHERE { ?run cmpo:executedOn ?c . FILTER(isIRI(?c)) } LIMIT 5"""),
    ("CQ10", "Which pad and pad lifetime is associated with a run?",
     "Pad wear / lifetime as drift factor (conditioning literature)",
     """SELECT ?pad ?v WHERE {
        inst:cmp_run_-4224160592_A_00282 cmpo:hasPolishingPad ?pad .
        OPTIONAL { ?p a cmpo:PadLifetime ;
                     cmpo:isMeasurementOf inst:cmp_run_-4224160592_A_00282 ;
                     cmpo:hasNumericValue ?v . } } LIMIT 5"""),
    ("CQ11", "Which layers or materials does a given wafer carry?",
     "Layer/material determines CMP step type (CMP intros)",
     """SELECT ?w ?m WHERE { ?w a cmpo:Wafer ; cmpo:hasMaterial ?m . } LIMIT 5"""),
    ("CQ12", "Which wafer lots exist and which wafers belong to them?",
     "Lot-level traceability (fab practice)",
     """SELECT ?lot ?w WHERE { ?w cmpo:hasLot ?lot . } LIMIT 5"""),
]


def experiment_3(datam):
    print("== E3: competency-question suite ==")
    out = []
    for cqid, text, prov, q in CQS:
        full = ("PREFIX cmpo: <https://tucid/cpmo/> "
                "PREFIX inst: <https://tucid/cpmo/instance/> "
                "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> " + q)
        try:
            rows = list(datam.query(full))
            nonempty = len(rows) > 0 and any(
                any(v is not None and str(v) not in ("", "0") for v in r)
                for r in rows)
            # counting queries: treat count>0 as non-empty
            out.append({"id": cqid, "question": text, "provenance": prov,
                        "executes": True, "rows": len(rows),
                        "nonempty": bool(nonempty),
                        "sample": [str(v)[:60] for v in rows[0]] if rows else []})
            print(f"  {cqid}: rows={len(rows)} nonempty={nonempty}")
        except Exception as e:
            out.append({"id": cqid, "question": text, "provenance": prov,
                        "executes": False, "error": str(e)[:120]})
            print(f"  {cqid}: FAILED {e}")
    return out


def main():
    t0 = time.time()
    ont, data, v1, v2 = load()
    ancestors = subclass_closure(ont)
    datam = materialise(data, ancestors)
    print(f"loaded; materialised graph {len(datam)} triples")

    RESULTS["E1"] = experiment_1(ont, data, datam, v1, v2)

    RESULTS["E2"] = experiment_2(ont, datam, v1, v2, None)
    RESULTS["E3"] = experiment_3(datam)

    RESULTS["runtime_seconds"] = round(time.time() - t0, 1)
    with open("evaluation/results.json", "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    print(f"done in {RESULTS['runtime_seconds']}s -> evaluation/results.json")


if __name__ == "__main__":
    main()
