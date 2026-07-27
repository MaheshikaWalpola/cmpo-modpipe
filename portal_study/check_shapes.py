#!/usr/bin/env python3
"""Injection test for a SHACL suite: does each shape actually enforce anything?

Motivation. A SHACL suite can load, validate, and return a clean report while
enforcing nothing at all: a shape may target a class with no instances, use a
property path that never occurs, or carry a constraint keyword the engine does
not recognise and therefore ignores. `pyshacl --metashacl` does not catch any
of these, because each of them is well-formed SHACL. The only reliable check is
to build a graph that violates every statement on purpose and confirm that each
shape fires on its own violation.

This script does that for the twenty validation statements in
`questions_20.md`. `probe20.ttl` contains one deliberately violating node per
statement, plus control nodes that must NOT fire. For each suite it reports:

  - loads          : whether the engine accepts the shapes graph at all
  - enforced       : statements whose own shape fired on their own probe node
  - inert          : statements whose shape is present but fired on nothing
  - absent         : statements with no shape in the suite
  - false positives: control nodes that fired although they are correct

The distinction between `advanced=True` and `advanced=False` matters. Advanced
mode is what SHACL-AF requires for any SPARQL-based constraint; it also
validates rule declarations, so a malformed `sh:rule` aborts the whole shapes
graph. Non-advanced mode ignores rules entirely, so the same suite loads and
silently drops those constraints. Both modes are reported, because a suite that
only works in one of them is a finding, not a detail.

Usage (from the repository root):
    python3 portal_study/check_shapes.py

Writes portal_study/results.json.
"""
import json
import os
import re
import sys

from rdflib import Graph, Namespace, RDF, RDFS
import pyshacl

SH = Namespace("http://www.w3.org/ns/shacl#")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SUITES = [
    ("run1_portal_generated", "portal_study/runs/run1_portal_generated.ttl"),
    ("run2_portal_generated", "portal_study/runs/run2_portal_generated.ttl"),
    ("run3_portal_generated", "portal_study/runs/run3_portal_generated.ttl"),
    ("shapes_corrected", "portal_study/shapes_corrected.ttl"),
    ("shapes_handwritten", "portal_study/shapes_handwritten.ttl"),
]

# probe node -> the statement number it is designed to violate.
# Nodes whose name ends in "ok" are controls: correct data that must not fire.
PROBE_MAP = {
    "obsQ1": 1, "obsQ2": 2, "obsQ3": 3, "obsQ4": 4, "obsQ5": 5, "obsQ6": 6,
    "wA": 7, "wB": 7, "stepQ8": 8, "toolQ9": 9, "chQ10": 10, "pzQ11": 11,
    "obsQ12": 12, "spcQ13": 13, "spcQ14": 14, "pwQ15": 15, "lotQ16": 16,
    "wQ17": 17, "wQ18": 18, "padQ19": 19, "prQ20": 20, "msQ20": 20,
}
CONTROLS = {"obsQ12ok"}


def _p(rel):
    return os.path.join(ROOT, rel)


def build_probe_graph():
    """probe + ontology, with the rdfs:subClassOf type closure materialised.

    Class-targeted shapes reach subclass members only if the subclass axioms
    are present in the validated graph; the portal materialises this closure
    before validating, so the probe run must do the same to be comparable.
    """
    data = Graph()
    data.parse(_p("portal_study/probe20.ttl"), format="turtle")
    data.parse(_p("ontology/schema_v2.1.ttl"), format="turtle")
    added = 1
    while added:
        added = 0
        for s, _, c in list(data.triples((None, RDF.type, None))):
            for sup in data.transitive_objects(c, RDFS.subClassOf):
                if (s, RDF.type, sup) not in data:
                    data.add((s, RDF.type, sup))
                    added += 1
    return data


def owning_node_shapes(shapes):
    """property shape (usually a blank node) -> the node shape that declares it.

    pySHACL reports sh:sourceShape as the *property* shape. Attributing a
    result back to a named rule therefore requires this lookup; skipping it is
    the defect that makes the portal report every rule as passed (see
    PROVENANCE.md).
    """
    owner = {}
    for ns in shapes.subjects(RDF.type, SH.NodeShape):
        for prop in shapes.objects(ns, SH.property):
            owner[prop] = ns
    return owner


def shape_statement(shapes, node):
    """Which statement number a shape belongs to.

    Suites label their shapes differently: the portal names them
    `inst:Question_N_Shape`, the corrected and hand-written suites carry the
    number in rdfs:label or in the sh:message of their constraints. All three
    conventions are resolved here so the suites are scored the same way.
    """
    name = str(node)
    m = re.search(r"Question_(\d+)_Shape", name)
    if m:
        return int(m.group(1))
    if "Tool_Identifier" in name:
        return 9        # emitted under a non-conforming name in every run
    label = str(shapes.value(node, RDFS.label) or "")
    m = re.match(r"\s*Q(\d+)", label)
    if m:
        return int(m.group(1))
    for prop in shapes.objects(node, SH.property):
        msg = str(shapes.value(prop, SH.message) or "")
        m = re.match(r"\s*Q(\d+)", msg)
        if m:
            return int(m.group(1))
    for sp in shapes.objects(node, SH.sparql):
        msg = str(shapes.value(sp, SH.message) or "")
        m = re.match(r"\s*Q(\d+)", msg)
        if m:
            return int(m.group(1))
    msg = str(shapes.value(node, SH.message) or "")
    m = re.match(r"\s*Q(\d+)", msg)
    return int(m.group(1)) if m else None


def statements_covered(shapes):
    """Statement numbers that have at least one shape in this suite."""
    covered = {}
    for s in shapes.subjects(RDF.type, SH.NodeShape):
        n = shape_statement(shapes, s)
        if n is not None:
            covered.setdefault(n, []).append(str(s))
    return covered


def run_suite(name, rel, data):
    shapes = Graph()
    shapes.parse(_p(rel), format="turtle")
    owner = owning_node_shapes(shapes)
    covered = statements_covered(shapes)
    out = {
        "file": rel,
        "node_shapes": len(set(shapes.subjects(RDF.type, SH.NodeShape))),
        "statements_with_a_shape": sorted(covered),
        "modes": {},
    }

    for advanced in (True, False):
        mode = {"advanced": advanced}
        try:
            conforms, rg, _ = pyshacl.validate(
                data, shacl_graph=shapes, inference="none", advanced=advanced)
        except Exception as exc:
            mode.update(loads=False, error=str(exc).split("\n")[0])
            out["modes"][f"advanced_{advanced}"] = mode
            continue

        fired = {}          # statement number -> True if its own shape fired
        false_positives = []
        for r in rg.subjects(RDF.type, SH.ValidationResult):
            focus = str(rg.value(r, SH.focusNode) or "")
            local = focus.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            src = rg.value(r, SH.sourceShape)
            node_shape = owner.get(src, src)
            if local in CONTROLS:
                false_positives.append(local)
                continue
            stmt = PROBE_MAP.get(local)
            if stmt is None:
                continue
            # Only count it when the shape that fired is the one written for
            # this statement. A shape that fires on everything (for example a
            # range check that rejects every punned observed property) would
            # otherwise be scored as detecting all twenty.
            owner_stmt = shape_statement(shapes, node_shape)
            if owner_stmt is None:
                # result attributed to a constraint whose message carries the
                # statement number directly (SPARQL constraints in the
                # corrected and hand-written suites)
                msg = str(rg.value(r, SH.resultMessage) or "")
                m2 = re.match(r"\s*Q(\d+)", msg)
                owner_stmt = int(m2.group(1)) if m2 else None
            if owner_stmt == stmt:
                fired[stmt] = True

        enforced = sorted(fired)
        present = set(out["statements_with_a_shape"])
        mode.update(
            loads=True,
            conforms=conforms,
            results=len(list(rg.subjects(RDF.type, SH.ValidationResult))),
            enforced=enforced,
            enforced_count=len(enforced),
            inert=sorted(present - set(enforced)),
            absent=sorted(set(range(1, 21)) - present),
            false_positive_control_nodes=sorted(set(false_positives)),
        )
        out["modes"][f"advanced_{advanced}"] = mode
    return out


def main():
    data = build_probe_graph()
    print(f"probe graph: {len(data)} triples "
          f"({len(PROBE_MAP)} violating nodes, {len(CONTROLS)} control node)\n")
    results = {"probe_triples": len(data), "suites": {}}
    for name, rel in SUITES:
        if not os.path.exists(_p(rel)):
            print(f"{name}: MISSING {rel}")
            continue
        r = run_suite(name, rel, data)
        results["suites"][name] = r
        print(f"{name}  ({r['node_shapes']} node shapes)")
        for key, m in r["modes"].items():
            if not m.get("loads"):
                print(f"   {key}: SHAPES GRAPH REJECTED - {m['error'][:90]}")
                continue
            print(f"   {key}: enforced {m['enforced_count']}/20 "
                  f"| inert {m['inert']} | absent {m['absent']}"
                  + (f" | FALSE POSITIVES {m['false_positive_control_nodes']}"
                     if m["false_positive_control_nodes"] else ""))
        print()

    with open(_p("portal_study/results.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    print("-> portal_study/results.json")


if __name__ == "__main__":
    sys.exit(main())
