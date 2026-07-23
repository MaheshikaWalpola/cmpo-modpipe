#!/usr/bin/env python3
"""End-to-end ModPipe run: generation -> validation gate -> persistence.

One command from the repository root:

    python3 modpipe/run_all.py

Stages 1-4 (ingestion/profiling, alignment, normalization, RDF generation)
run via modpipe.py and write out/kg_unvalidated.ttl. Stage 5 runs the
two-tier gate exactly as the evaluation harness does (tier 1: pySHACL over
the union of graph and ontology; tier 2: the three graph-level SPARQL
rules). Stage 6 persists the graph together with its validation report:
out/kg_cmpo.ttl and out/validation_report.json, so the conformance status
ships with the graph instead of gating it silently.

Requires the PHM 2016 CSVs in data/ (see data/README.txt).
"""
import json
import runpy
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

t0 = time.time()

# Stages 1-4: generation (modpipe.py resolves its inputs repo-relative).
print("[run_all] stages 1-4: generation (modpipe.py)", flush=True)
runpy.run_path(str(HERE / "modpipe.py"), run_name="__main__")

# Stage 5: the two-tier validation gate, reusing the harness implementation
# so the gate here and the gate measured in the paper are the same code.
print("[run_all] stage 5: validation gate", flush=True)
import importlib.util
spec = importlib.util.spec_from_file_location("ev", str(HERE / "evaluate_v2.py"))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

from rdflib import Graph

GEN = HERE / "out" / "kg_unvalidated.ttl"   # written by modpipe.py in stage 4
ont = Graph(); ont.parse(ev._find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl"), format="turtle")
kg = Graph(); kg.parse(str(GEN), format="turtle")
core = Graph(); core.parse(ev._find("shapes/shapes_core.ttl", "shapes_core.ttl"), format="turtle")
u = ev.union(kg, ont)
conforms, n_tier1, tier1_focus = ev.run_val(u, core)
tier2_counts, tier2_focus = ev.tier2_audit(u)

report = {
    "graph_triples": len(kg),
    "union_triples": len(u),
    "tier1_conforms": bool(conforms),
    "tier1_violations": n_tier1,
    "tier1_focus_nodes": sorted({fn for fn, _, _ in tier1_focus}),
    "tier2_rule_hits": tier2_counts,
    "tier2_focus_nodes": sorted({fn for fn, _, _ in tier2_focus}),
    "gate_seconds": round(time.time() - t0, 1),
}

# Stage 6: persistence -- graph and report side by side.
print("[run_all] stage 6: persistence", flush=True)
out = HERE / "out"
out.mkdir(exist_ok=True)
shutil.copyfile(GEN, out / "kg_cmpo.ttl")
json.dump(report, open(out / "validation_report.json", "w"), indent=2)

print(f"[run_all] done in {round(time.time() - t0, 1)}s")
print(f"[run_all] graph: out/kg_cmpo.ttl ({len(kg)} triples)")
print(f"[run_all] report: out/validation_report.json "
      f"(tier1 conforms={report['tier1_conforms']}, "
      f"violations={report['tier1_violations']})")
