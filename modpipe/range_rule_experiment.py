#!/usr/bin/env python3
"""T7 range-rule experiment (R7): extend the tier-2 gate with a per-parameter
operating-range rule and measure detection on the E2 seeded-error study.

Protocol (frozen 2026-07-23 in hiwi_t7_range_experiment_protocol.md):
1. derive per-observed-property bounds from the CLEAN evaluation subgraph,
   widened to [min - 0.5*span, max + 0.5*span]; span=0 -> [v-0.5|v|-1, v+0.5|v|+1];
   write evaluation/range_bounds.csv BEFORE running anything else (frozen).
2. R7 = SPARQL audit query in TIER2_QUERIES style: flag observations whose
   numeric value lies outside the bounds of their observed property.
3. sanity: R7 on the clean subgraph must report 0.
4. rerun E2 with a fourth condition tier1+2+R7, seed 42, same 8 operators,
   same differential criterion. Harness functions are imported, not copied.
5. pre-registered expectation: T7 flips to detected, T5 stays undetected,
   all other rows unchanged. Any deviation is a finding to report.

Reported as Table 3 of the SemIIM 2026 paper, as an extension to the
submitted taxonomy: R7 was designed after Table 2 was frozen and is never
merged into Table 2's conditions.
"""
import csv
import importlib.util
import json
import os
import sys

# Reproducibility pin: the harness samples T3/T5/T7 target observations by
# RNG-shuffling rdflib SPARQL result rows whose ORDER depends on the Python
# hash seed. The submitted paper's E2 numbers are invariant to this (its
# detections are 0, 50, or all-seeded regardless of which observations were
# sampled), but R7 detection counts are not. Pin the hash seed so this
# experiment is reproducible run-to-run.
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

from rdflib import Graph  # noqa: E402  (after ev import, mirroring multiseed_e2.py)

PFX = ("PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#> "
       "PREFIX sosa: <http://www.w3.org/ns/sosa/> "
       "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> ")

R = {}

ont, kg, core, both = ev.load()
sub = ev.build_subgraph(kg, ont)   # consumes the same RNG(42) draws as the harness
print(f"subgraph: {len(sub)} triples (incl. ontology)", flush=True)

# --- 1. derive bounds per observed property on the clean subgraph ------------
rows = sub.query(PFX + """
    SELECT ?p ?v WHERE {
        ?o a cmpo:CMPObservation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
        FILTER(isNumeric(?v)) }""")
vals = {}
for p, v in rows:
    vals.setdefault(str(p), []).append(float(v))

bounds = {}
for p, vs in sorted(vals.items()):
    mn, mx = min(vs), max(vs)
    span = mx - mn
    if span == 0:
        lo, hi = mn - 0.5 * abs(mn) - 1, mn + 0.5 * abs(mn) + 1
    else:
        lo, hi = mn - 0.5 * span, mx + 0.5 * span
    bounds[p] = (lo, hi, mn, mx, len(vs))

os.makedirs("evaluation", exist_ok=True)
with open("evaluation/range_bounds.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["observed_property", "n_values_clean", "min_clean", "max_clean", "lower_bound", "upper_bound"])
    for p, (lo, hi, mn, mx, n) in sorted(bounds.items()):
        w.writerow([p, n, mn, mx, lo, hi])
print(f"bounds for {len(bounds)} observed properties -> evaluation/range_bounds.csv (frozen)", flush=True)

# --- 2. rule R7 as a SPARQL audit query --------------------------------------
# bounds as xsd:double e-notation literals: rdflib's SPARQL parser rejects
# negative xsd:decimal literals inside VALUES (upstream bug), doubles parse fine
values_block = " ".join(
    "( <%s> %.17e %.17e )" % (p, lo, hi) for p, (lo, hi, _, _, _) in sorted(bounds.items()))
R7_QUERY = PFX + """
    SELECT ?this WHERE {
        ?this sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
        VALUES (?p ?lo ?hi) { %s }
        FILTER (isNumeric(?v) && (?v < ?lo || ?v > ?hi)) }""" % values_block

def r7_audit(data):
    """R7 in the exact style of ev.tier2_audit: returns (count, focus-set)."""
    found = set()
    for r in data.query(R7_QUERY):
        found.add((str(r[0]), "R7_range", "SPARQLRule"))
    return len(found), found

# --- 3. sanity check on the clean subgraph -----------------------------------
n_clean, _ = r7_audit(sub)
R["clean_sanity_R7_violations"] = n_clean
print(f"sanity: R7 on clean subgraph = {n_clean} (must be 0)", flush=True)
if n_clean != 0:
    json.dump(R, open("evaluation/range_rule_results.json", "w"), indent=2)
    raise SystemExit("R7 fires on the clean subgraph; stopping per protocol step 3.")

# --- 4. E2 rerun with the fourth condition tier1+2+R7 ------------------------
# Clean baselines per condition (differential criterion, as in ev.experiment_2).
_, n0, f0 = ev.run_val(sub, core)
_, f0b = ev.tier2_audit(sub)
_, f0c = r7_audit(sub)
base = {"tier1": f0, "tier12": f0 | f0b, "tier12r7": f0 | f0b | f0c}
print(f"clean baseline: tier1={n0} violations, tier2 extra={len(f0b)}, R7 extra={len(f0c)}", flush=True)

OPS = ["T1_missing_value", "T2_datatype", "T3_negative_value", "T4_dangling_foi",
       "T5_plausible_swap", "T6_undeclared_property", "T7_unit_scale", "T8_duplicate_wafer"]
out = {}
from rdflib import Namespace
SOSA = Namespace("http://www.w3.org/ns/sosa/")

def seeded_vs_bounds(g, seeded):
    """Diagnostic only: how many seeded observations actually lie outside
    their property's frozen bounds, and how many carry a zero value."""
    outside = zeros = 0
    for s in seeded:
        p = next(iter(g.objects(s, SOSA.observedProperty)), None)
        v = next(iter(g.objects(s, SOSA.hasSimpleResult)), None)
        if p is None or v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == 0:
            zeros += 1
        if str(p) in bounds:
            lo, hi = bounds[str(p)][0], bounds[str(p)][1]
            if f < lo or f > hi:
                outside += 1
    return outside, zeros

for op in OPS:
    undo, seeded = ev.seed(sub, op)
    row = {"seeded": len(seeded)}
    if op in ("T5_plausible_swap", "T7_unit_scale"):
        row["seeded_outside_bounds"], row["seeded_zero_values"] = seeded_vs_bounds(sub, seeded)
    _, _, focus1 = ev.run_val(sub, core)
    _, focus2 = ev.tier2_audit(sub)
    _, focus3 = r7_audit(sub)
    for lbl, focus in [("tier1", focus1),
                       ("tier12", focus1 | focus2),
                       ("tier12r7", focus1 | focus2 | focus3)]:
        new = focus - base[lbl]
        det = sum(1 for s in seeded if any(str(s).rsplit('#', 1)[-1] in fn for fn, _, _ in new))
        row[lbl] = det
    removed, added = undo
    for t in added:
        Graph.remove(sub, t)
    for t in removed:
        Graph.add(sub, t)
    out[op] = row
    print(f"  {op}: seeded={row['seeded']} tier1={row['tier1']} "
          f"tier12={row['tier12']} tier12+R7={row['tier12r7']}", flush=True)

R["bounds_properties"] = len(bounds)
R["pythonhashseed"] = os.environ.get("PYTHONHASHSEED")
R["E2_with_R7"] = out
json.dump(R, open("evaluation/range_rule_results.json", "w"), indent=2)
print("done -> evaluation/range_rule_results.json", flush=True)
