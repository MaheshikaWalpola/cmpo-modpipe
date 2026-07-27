#!/usr/bin/env python3
"""R7 sensitivity: are the Table 3 detection counts an artifact of the two
free parameters, the seeding size k and the bound-widening constant?

range_rule_experiment.py reports one operating point: k = 50 (100 corrupted
nodes for the pairwise swap) and bounds widened by half the observed span.
Both numbers are choices. This script varies each one and reports how far the
detection rates move, so the paper can state the sensitivity instead of
asserting that the choices did not matter.

Two sweeps, both on the clean E2 evaluation subgraph (seed 42):

  A. k from 50 to 600, widening held at 0.5. The sampling pool is the set of
     non-negative pressure observations in the subgraph, so k is bounded by
     that pool (the swap operator consumes two observations per pair).

  C. the census: seed EVERY eligible observation rather than a sample, which
     removes the sampling question entirely. The pool is small enough (1,259
     non-negative pressure observations) that this is cheap, and it gives the
     exact detection rate for the subgraph instead of an estimate.

  B. widening factor 0, 0.25, 0.5 and 1.0, k held at 50. Also reports the
     false positives each factor produces on the clean subgraph, which must
     be zero at every setting: the bounds are derived from that same data, so
     widening can only ever enlarge an interval that already contains it.

Sampling note: each condition resets the RNG to Random(42) before seeding, so
that conditions differ by the parameter under test and not by which
observations were drawn. The main harness instead lets one RNG stream run
through all eight operators in sequence, so its k = 50 counts come from a
different draw than this script's k = 50 point. The two are independent
samples of the same quantity, which is why this script reports rates.

Usage: PYTHONHASHSEED=0 python3 modpipe/range_rule_sensitivity.py
Writes evaluation/range_rule_sensitivity.json.
"""
import importlib.util
import json
import os
import random
import sys

if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _find(*cands):
    for c in cands:
        if os.path.exists(c):
            return c
    raise FileNotFoundError("none of: " + ", ".join(cands) + " -- run from the repository root")


spec = importlib.util.spec_from_file_location("ev", _find("modpipe/evaluate_v2.py", "evaluate_v2.py"))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

from rdflib import Graph, Namespace, RDF  # noqa: E402

SOSA = Namespace("http://www.w3.org/ns/sosa/")
CMPO = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#")
PFX = ("PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#> "
       "PREFIX sosa: <http://www.w3.org/ns/sosa/> "
       "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> ")

K_VALUES = [50, 100, 200, 400, 600]
WIDEN_VALUES = [0.0, 0.25, 0.5, 1.0]
BASE_WIDEN = 0.5
BASE_K = 50


def derive_bounds(g, widen):
    """Per-observed-property interval, widened by `widen` times the span.
    Same rule as range_rule_experiment.py, with the constant exposed."""
    rows = g.query(PFX + """
        SELECT ?p ?v WHERE {
            ?o a cmpo:CMPObservation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
            FILTER(isNumeric(?v)) }""")
    vals = {}
    for p, v in rows:
        vals.setdefault(str(p), []).append(float(v))
    bounds = {}
    for p, vs in vals.items():
        mn, mx = min(vs), max(vs)
        span = mx - mn
        if span == 0:
            bounds[p] = (mn - widen * abs(mn) - 1, mn + widen * abs(mn) + 1)
        else:
            bounds[p] = (mn - widen * span, mx + widen * span)
    return bounds


def detected(g, bounds, seeded):
    """How many seeded observations now lie outside their property's interval."""
    n = 0
    for s in seeded:
        p = next(iter(g.objects(s, SOSA.observedProperty)), None)
        v = next(iter(g.objects(s, SOSA.hasSimpleResult)), None)
        if p is None or v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        lo_hi = bounds.get(str(p))
        if lo_hi and (f < lo_hi[0] or f > lo_hi[1]):
            n += 1
    return n


def clean_false_positives(g, bounds):
    """Every hit here is a false positive: the graph is uncorrupted."""
    n = 0
    for o, _, v in g.triples((None, SOSA.hasSimpleResult, None)):
        p = next(iter(g.objects(o, SOSA.observedProperty)), None)
        if p is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        lo_hi = bounds.get(str(p))
        if lo_hi and (f < lo_hi[0] or f > lo_hi[1]):
            n += 1
    return n


def run_op(g, op, k, bounds):
    ev.RNG = random.Random(42)
    undo, seeded = ev.seed(g, op, k=k)
    d = detected(g, bounds, seeded)
    n = len(seeded)
    removed, added = undo
    for t in added:
        Graph.remove(g, t)
    for t in removed:
        Graph.add(g, t)
    return n, d


R = {"note": "detection rates for the two error classes the released gate misses"}

ont, kg, core, both = ev.load()
sub = ev.build_subgraph(kg, ont)
print(f"subgraph: {len(sub)} triples", flush=True)

pool = len(list(sub.query(PFX + """
    SELECT ?o WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
        ?p rdfs:subClassOf* cmpo:Pressure . FILTER(?v >= 0) }""")))
zeros = len(list(sub.query(PFX + """
    SELECT ?o WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
        ?p rdfs:subClassOf* cmpo:Pressure . FILTER(?v = 0) }""")))
R["pool"] = {"non_negative_pressure_observations": pool, "of_which_exactly_zero": zeros}
print(f"sampling pool: {pool} non-negative pressure observations, {zeros} of them zero", flush=True)

# --- sweep A: seeding size -------------------------------------------------
base_bounds = derive_bounds(sub, BASE_WIDEN)
R["A_k_sweep"] = {"widening": BASE_WIDEN, "points": []}
print(f"\n{'k':>6} {'T7 n':>6} {'T7 det':>7} {'T7 %':>7} {'T5 n':>6} {'T5 det':>7} {'T5 %':>7}", flush=True)
for k in K_VALUES:
    n7, d7 = run_op(sub, "T7_unit_scale", k, base_bounds)
    n5, d5 = run_op(sub, "T5_plausible_swap", k, base_bounds)
    R["A_k_sweep"]["points"].append({
        "k": k,
        "T7": {"seeded": n7, "detected": d7, "rate_pct": round(100.0 * d7 / n7, 2) if n7 else None},
        "T5": {"seeded": n5, "detected": d5, "rate_pct": round(100.0 * d5 / n5, 2) if n5 else None},
    })
    print(f"{k:>6} {n7:>6} {d7:>7} {100.0*d7/max(n7,1):>6.1f}% {n5:>6} {d5:>7} {100.0*d5/max(n5,1):>6.1f}%", flush=True)

# --- sweep B: widening constant -------------------------------------------
R["B_widening_sweep"] = {"k": BASE_K, "points": []}
print(f"\n{'widen':>6} {'T7 det':>7} {'T5 det':>7} {'clean FP':>9}", flush=True)
for w in WIDEN_VALUES:
    b = derive_bounds(sub, w)
    fp = clean_false_positives(sub, b)
    n7, d7 = run_op(sub, "T7_unit_scale", BASE_K, b)
    n5, d5 = run_op(sub, "T5_plausible_swap", BASE_K, b)
    R["B_widening_sweep"]["points"].append({
        "widening": w, "clean_false_positives": fp,
        "T7": {"seeded": n7, "detected": d7},
        "T5": {"seeded": n5, "detected": d5},
    })
    print(f"{w:>6} {d7:>3}/{n7:<3} {d5:>3}/{n5:<3} {fp:>9}", flush=True)

# --- C: census, every eligible observation -------------------------------
R["C_census"] = {"widening": BASE_WIDEN, "pool": pool, "points": []}
print(f"\n{'operator':<10} {'seeded':>7} {'detected':>9} {'rate':>7}", flush=True)
for op, kmax, lbl in [("T7_unit_scale", pool, "T7"), ("T5_plausible_swap", pool // 2, "T5")]:
    n, d = run_op(sub, op, kmax, base_bounds)
    R["C_census"]["points"].append({"class": lbl, "seeded": n, "detected": d,
                                    "rate_pct": round(100.0 * d / n, 2) if n else None})
    print(f"{lbl:<10} {n:>7} {d:>9} {100.0*d/max(n,1):>6.1f}%", flush=True)

R["pythonhashseed"] = os.environ.get("PYTHONHASHSEED")
os.makedirs("evaluation", exist_ok=True)
json.dump(R, open("evaluation/range_rule_sensitivity.json", "w"), indent=2)
print("\ndone -> evaluation/range_rule_sensitivity.json", flush=True)
