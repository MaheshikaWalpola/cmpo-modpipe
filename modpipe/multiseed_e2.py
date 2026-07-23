#!/usr/bin/env python3
"""E2 seeded-error study under additional seeds (7, 123) to test whether the
detected-class set and detection counts depend on the sampling/mutation seed.
Reuses the released harness functions unchanged."""
import json, random, time
import os as _os
def _find(*cands):
    for c in cands:
        if _os.path.exists(c): return c
    raise FileNotFoundError("none of: " + ", ".join(cands) + " -- run from the repository root")

import importlib.util
spec = importlib.util.spec_from_file_location("ev", _find("modpipe/evaluate_v2.py", "evaluate_v2.py"))
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
from rdflib import Graph

ont = Graph(); ont.parse(_find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl"), format="turtle")
kg = Graph(); kg.parse(_find("kg/kg_cmpo_v2.0.2.ttl", "kg_cmpo_v202.ttl"), format="turtle")
out = {}
for seed in [7, 123]:
    t0 = time.time()
    ev.RNG = random.Random(seed)
    sub = ev.build_subgraph(kg, ont)
    core = Graph(); core.parse(_find("shapes/shapes_core.ttl", "shapes_core.ttl"), format="turtle")
    res = ev.experiment_2(sub, core, None)
    out[str(seed)] = {"subgraph_triples": len(sub),
                      "results": {op: {"seeded": r["seeded"], "tier1": r["tier1"], "tier12": r["tier12"]}
                                  for op, r in res.items()},
                      "runtime_s": round(time.time() - t0, 1)}
    print("seed", seed, "done", flush=True)
json.dump(out, open("multiseed_e2_results.json", "w"), indent=2)
print("all done", flush=True)
