#!/usr/bin/env python3
"""R7 transfer study: do data-derived per-parameter bounds hold outside the
sample they were derived from?

The detection counts in range_rule_experiment.py are measured on the same
4,000-observation subgraph the bounds were derived from, so every uncorrupted
value lies inside the bounds by construction. That makes the counts a proof of
mechanism and nothing more. This script asks the separate question an adopter
would ask: if we shipped those bounds as a rule, how often would they fire on
data they were not derived from?

Two conditions, both measured as a false-positive rate on clean data:

  A. Held-out observations. Bounds from the 4,000-observation evaluation
     subgraph (seed 42, the same RNG stream as the harness), evaluated on every
     other observation in the released graph. These come from the same four
     wafers, so this is the optimistic case.

  B. Leave-one-wafer-out. For each PHM wafer in turn, derive bounds from the
     other three wafers only and evaluate on the held-out wafer. This is the
     honest test of whether an interval learned on some wafers transfers to a
     wafer it has never seen. Reported pooled and per wafer.

A property present in the evaluation set but absent from the training set
cannot be checked at all; those observations are counted separately as
"unchecked" rather than silently as passes.

Usage: PYTHONHASHSEED=0 python3 modpipe/range_rule_transfer.py
Writes evaluation/range_rule_transfer.json.
"""
import importlib.util
import json
import os
import sys
from collections import defaultdict

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

PFX = ("PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#> "
       "PREFIX sosa: <http://www.w3.org/ns/sosa/> ")

OBS_QUERY = PFX + """
    SELECT ?o ?p ?v ?w WHERE {
        ?o a cmpo:CMPObservation ;
           sosa:observedProperty ?p ;
           sosa:hasSimpleResult ?v .
        OPTIONAL { ?o sosa:hasFeatureOfInterest ?w }
        FILTER(isNumeric(?v)) }"""


def derive_bounds(records):
    """Same widening rule as range_rule_experiment.py, protocol step 1."""
    vals = defaultdict(list)
    for _, p, v, _ in records:
        vals[p].append(v)
    bounds = {}
    for p, vs in vals.items():
        mn, mx = min(vs), max(vs)
        span = mx - mn
        if span == 0:
            lo, hi = mn - 0.5 * abs(mn) - 1, mn + 0.5 * abs(mn) + 1
        else:
            lo, hi = mn - 0.5 * span, mx + 0.5 * span
        bounds[p] = (lo, hi)
    return bounds


def evaluate(bounds, records):
    """Apply bounds to clean records. Every hit is a false positive."""
    flagged = unchecked = 0
    for _, p, v, _ in records:
        if p not in bounds:
            unchecked += 1
            continue
        lo, hi = bounds[p]
        if v < lo or v > hi:
            flagged += 1
    return flagged, unchecked


R = {"protocol": "bounds widened to [min - 0.5*span, max + 0.5*span]; "
                 "flagged counts on clean data are false positives"}

ont, kg, core, both = ev.load()

records = []
for o, p, v, w in kg.query(OBS_QUERY):
    records.append((str(o), str(p), float(v), str(w) if w is not None else None))
print(f"observations with a numeric result: {len(records)}", flush=True)

# The evaluation subgraph is built from the same RNG stream as the harness, so
# rebuilding it here identifies exactly the observations the bounds came from.
sub = ev.build_subgraph(kg, ont)
sample_ids = {str(s) for s in sub.subjects(ev.RDF.type, ev.CMPO.CMPObservation)} \
    if hasattr(ev, "RDF") and hasattr(ev, "CMPO") else None
if sample_ids is None:
    from rdflib import RDF, Namespace
    CMPO = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#")
    sample_ids = {str(s) for s in sub.subjects(RDF.type, CMPO.CMPObservation)}
print(f"evaluation subgraph observations: {len(sample_ids)}", flush=True)

# --- condition A: held-out observations, same wafers -------------------------
in_sample = [r for r in records if r[0] in sample_ids]
held_out = [r for r in records if r[0] not in sample_ids]
bounds_sample = derive_bounds(in_sample)
flagged, unchecked = evaluate(bounds_sample, held_out)
R["A_held_out_same_wafers"] = {
    "bounds_from": len(in_sample),
    "bounds_properties": len(bounds_sample),
    "evaluated": len(held_out),
    "flagged": flagged,
    "unchecked_property_absent_from_training": unchecked,
    "false_positive_rate_pct": round(100.0 * flagged / len(held_out), 4) if held_out else None,
}
print(f"A held-out: {flagged}/{len(held_out)} flagged "
      f"({100.0 * flagged / max(len(held_out), 1):.4f}%), {unchecked} unchecked", flush=True)

# --- condition B: leave one wafer out ----------------------------------------
# PHM wafers only: the synthetic completion sample is not physically
# representative and its wafers are special-purpose, so pooling them into a
# transfer test would measure the generator, not the process.
by_wafer = defaultdict(list)
for r in records:
    if r[3]:
        by_wafer[r[3]].append(r)
# The four PHM wafers are the instances typed directly as cmpo:Wafer; the
# synthetic completion sample uses subclasses (DummyWafer, ControlWafer,
# StructuredWafer), so this criterion selects the real process wafers exactly.
real_wafers = {str(s) for s in kg.subjects(ev.RDF.type, ev.CMPO.Wafer)} \
    if hasattr(ev, "RDF") and hasattr(ev, "CMPO") else None
if real_wafers is None:
    from rdflib import RDF, Namespace
    CMPO = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#")
    real_wafers = {str(s) for s in kg.subjects(RDF.type, CMPO.Wafer)}
phm_wafers = sorted(w for w in by_wafer if w in real_wafers)
print(f"wafers used for leave-one-out: {[w.rsplit('#', 1)[-1] for w in phm_wafers]}", flush=True)

per_wafer, tot_eval, tot_flag, tot_unchecked = [], 0, 0, 0
for w in phm_wafers:
    train = [r for x in phm_wafers if x != w for r in by_wafer[x]]
    test = by_wafer[w]
    b = derive_bounds(train)
    f, u = evaluate(b, test)
    per_wafer.append({
        "wafer": w.rsplit("#", 1)[-1].rsplit("/", 1)[-1],
        "trained_on": len(train),
        "evaluated": len(test),
        "flagged": f,
        "unchecked": u,
        "false_positive_rate_pct": round(100.0 * f / len(test), 4) if test else None,
    })
    tot_eval += len(test)
    tot_flag += f
    tot_unchecked += u
    print(f"  LOWO {per_wafer[-1]['wafer']}: {f}/{len(test)} "
          f"({100.0 * f / max(len(test), 1):.4f}%)", flush=True)

R["B_leave_one_wafer_out"] = {
    "wafers": len(phm_wafers),
    "pooled_evaluated": tot_eval,
    "pooled_flagged": tot_flag,
    "pooled_unchecked": tot_unchecked,
    "pooled_false_positive_rate_pct": round(100.0 * tot_flag / tot_eval, 4) if tot_eval else None,
    "per_wafer": per_wafer,
}
print(f"B pooled: {tot_flag}/{tot_eval} flagged "
      f"({100.0 * tot_flag / max(tot_eval, 1):.4f}%)", flush=True)

R["pythonhashseed"] = os.environ.get("PYTHONHASHSEED")
os.makedirs("evaluation", exist_ok=True)
json.dump(R, open("evaluation/range_rule_transfer.json", "w"), indent=2)
print("done -> evaluation/range_rule_transfer.json", flush=True)
