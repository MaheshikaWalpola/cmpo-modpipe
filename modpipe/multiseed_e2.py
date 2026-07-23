#!/usr/bin/env python3
"""E2 seeded-error study under additional seeds (7, 123) to test whether the
detected-class set and detection counts depend on the sampling/mutation seed.
Reuses the released harness functions unchanged."""
import json, random, time, importlib.util
spec = importlib.util.spec_from_file_location("ev", "evaluate_v2.py")
ev = importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
from rdflib import Graph

ont = Graph(); ont.parse("cmpo-v2.0.2.ttl", format="turtle")
kg = Graph(); kg.parse("kg_cmpo_v202.ttl", format="turtle")
out = {}
for seed in [7, 123]:
    t0 = time.time()
    ev.RNG = random.Random(seed)
    sub = ev.build_subgraph(kg, ont)
    core = Graph(); core.parse("shapes_core.ttl", format="turtle")
    res = ev.experiment_2(sub, core, None)
    out[str(seed)] = {"subgraph_triples": len(sub),
                      "results": {op: {"seeded": r["seeded"], "tier1": r["tier1"], "tier12": r["tier12"]}
                                  for op, r in res.items()},
                      "runtime_s": round(time.time() - t0, 1)}
    print("seed", seed, "done", flush=True)
json.dump(out, open("multiseed_e2_results.json", "w"), indent=2)
print("all done", flush=True)
