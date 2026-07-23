#!/usr/bin/env python3
"""ModPipe: modular pipeline from heterogeneous CMP process tables to a
validated knowledge graph aligned with CMPO v2.0.1.

Stages (each leaves an inspectable artifact in out/):
  1 ingestion+profiling   -> out/profile.json
  2 ontology alignment    -> reads the declarative mapping spec (CSV)
  3 value normalization   -> applied in-stream (floats, ISO timestamps; raw kept)
  4 RDF generation        -> out/kg_unvalidated.ttl
  5 SHACL validation gate -> out/validation_report.txt (+ gate verdict)
  6 persistence           -> out/kg_validated.ttl (only if gate passes / report attached)

Inputs: PHM 2016 CMP CSVs + synthetic completion table (clearly marked provenance).
Every triple traces to a source cell; no LLM in the loop.
"""
import csv as csvmod
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import os as _os
def _find(*cands):
    for c in cands:
        if _os.path.exists(c): return c
    raise FileNotFoundError("none of: " + ", ".join(cands) + " -- run from the repository root")

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

CMPO = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
INST = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo/instance#")

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

MAPPING_CSV = _find("mapping/csv_to_cmpo_v2.0_mapping_test_sample.csv", "csv_to_cmpo_v2.0_mapping_test_sample.csv")
SYNTH_XLSX = _find("synthetic/CMPO_v2.0_Synthetic_Completion_Table_test_sample.xlsx", "CMPO_v2.0_Synthetic_Completion_Table_test_sample.xlsx")
ONTOLOGY = _find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl")
PROCESS_CSV = _find("data/CMP-test-000.csv", "CMP-test-000.csv")  # obtain from the PHM Society 2016 Data Challenge (see data/README.txt); place in data/
RR_CSV = _find("data/CMP-test-removalrate.csv", "CMP-test-removalrate.csv")  # same source as PROCESS_CSV

# measurement column -> observable-property class comes from the mapping spec;
# identifier/context columns are handled structurally per its rdf_pattern notes.
IDENT_COLS = {"MACHINE_ID", "MACHINE_DATA", "TIMESTAMP", "WAFER_ID", "STAGE", "CHAMBER"}


def stage1_profile():
    prof = {}
    for path in [PROCESS_CSV, RR_CSV]:
        df = pd.read_csv(path)
        prof[Path(path).name] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
            "n_columns": int(df.shape[1]),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "missing_cells": int(df.isna().sum().sum()),
            "distinct_wafers": int(df["WAFER_ID"].nunique()) if "WAFER_ID" in df else None,
        }
    (OUT / "profile.json").write_text(json.dumps(prof, indent=2))
    return prof


def stage2_alignment():
    rows = list(csvmod.DictReader(open(MAPPING_CSV)))
    meas = {}
    for r in rows:
        if r["role"].startswith("measurement"):
            term = r["cmpo_term"].split()[0].replace("cmpo:", "")
            meas[r["csv_column"]] = term
    return rows, meas


def iso(epoch):
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def stage34_generate(meas_map):
    g = Graph()
    g.bind("cmpo", CMPO); g.bind("sosa", SOSA); g.bind("", INST)
    df = pd.read_csv(PROCESS_CSV)
    stats = {"rows": len(df), "observations": 0, "cells_skipped_missing": 0}
    seen = set()

    def ent(node, cls, prop=None, val=None, dt=None):
        if node not in seen:
            g.add((node, RDF.type, cls)); seen.add(node)
        if prop is not None and val is not None:
            if (node, prop, None) not in g:
                g.add((node, prop, Literal(val, datatype=dt)))

    for i, row in df.iterrows():
        wafer = INST[f"wafer_{row['WAFER_ID']}"]
        ent(wafer, CMPO.Wafer, CMPO.hasWaferId, str(row["WAFER_ID"]), XSD.string)
        machine = INST[f"machine_{row['MACHINE_ID']}"]
        ent(machine, CMPO.Tool, CMPO.toolId, str(row["MACHINE_ID"]), XSD.string)
        chamber = INST[f"chamber_{int(row['CHAMBER'])}"]
        ent(chamber, CMPO.Chamber, CMPO.chamberNumber, int(row["CHAMBER"]), XSD.integer)
        step = INST[f"step_{row['STAGE']}_{row['WAFER_ID']}"]
        ent(step, CMPO.PolishingStep, CMPO.stageLabel, str(row["STAGE"]), XSD.string)

        for col, cls_name in meas_map.items():
            if col not in df.columns:
                continue
            v = row[col]
            if pd.isna(v):
                stats["cells_skipped_missing"] += 1
                continue
            obs = INST[f"obs_{row['WAFER_ID']}_{row['STAGE']}_{i:05d}_{col}"]
            g.add((obs, RDF.type, CMPO.CMPObservation))
            g.add((obs, SOSA.observedProperty, CMPO[cls_name]))
            g.add((obs, SOSA.hasFeatureOfInterest, wafer))
            g.add((obs, CMPO.madeOnPlatform, machine))
            g.add((obs, CMPO.madeOnPlatform, chamber))
            g.add((obs, CMPO.duringStep, step))
            g.add((obs, SOSA.hasSimpleResult, Literal(float(v), datatype=XSD.float)))
            g.add((obs, CMPO.machineDataId, Literal(int(row["MACHINE_DATA"]), datatype=XSD.integer)))
            g.add((obs, CMPO.rawTimestamp, Literal(row["TIMESTAMP"], datatype=XSD.decimal)))
            t = iso(row["TIMESTAMP"])
            if t:
                g.add((obs, SOSA.resultTime, Literal(t, datatype=XSD.dateTime)))
            stats["observations"] += 1

    rr = pd.read_csv(RR_CSV)
    stats["rr_rows_total_file"] = len(rr)
    # scope the removal-rate labels to the wafers of the ingested process file
    proc_wafers = set(df["WAFER_ID"].astype(str))
    rr = rr[rr["WAFER_ID"].astype(str).isin(proc_wafers)]
    stats["rr_rows"] = len(rr)
    for i, row in rr.iterrows():
        wafer = INST[f"wafer_{row['WAFER_ID']}"]
        ent(wafer, CMPO.Wafer, CMPO.hasWaferId, str(row["WAFER_ID"]), XSD.string)
        step = INST[f"step_{row['STAGE']}_{row['WAFER_ID']}"]
        ent(step, CMPO.PolishingStep, CMPO.stageLabel, str(row["STAGE"]), XSD.string)
        obs = INST[f"obs_rr_{row['WAFER_ID']}_{row['STAGE']}_{i:05d}"]
        g.add((obs, RDF.type, CMPO.CMPObservation))
        g.add((obs, SOSA.observedProperty, CMPO.AverageRemovalRate))
        g.add((obs, SOSA.hasFeatureOfInterest, wafer))
        g.add((obs, CMPO.duringStep, step))
        g.add((obs, SOSA.hasSimpleResult, Literal(float(row["AVG_REMOVAL_RATE"]), datatype=XSD.float)))
        stats["observations"] += 1
    return g, stats


DT = {"xsd:string": XSD.string, "xsd:integer": XSD.integer, "xsd:decimal": XSD.decimal,
      "xsd:float": XSD.float, "xsd:double": XSD.double, "xsd:date": XSD.date,
      "xsd:dateTime": XSD.dateTime, "xsd:boolean": XSD.boolean}


def term(v):
    v = str(v).strip()
    if v.startswith("cmpo:"):
        return CMPO[v[5:]]
    if v.startswith("sosa:"):
        return SOSA[v[5:]]
    if v.startswith("rdf:type"):
        return RDF.type
    return INST[v]


def stage_synth(g):
    """Ingest the synthetic completion sample (provenance-marked syn_ IRIs)."""
    x = pd.ExcelFile(SYNTH_XLSX)
    ents = x.parse("Synthetic_Entities")
    n_ent_triples = 0
    for _, r in ents.iterrows():
        s = INST[str(r["entity_id"])]
        p = term(r["property"])
        if str(r["value_kind"]).strip() == "IRI":
            o = term(r["value"])
        else:
            o = Literal(str(r["value"]), datatype=DT.get(str(r["value_kind"]).strip()))
        g.add((s, p, o)); n_ent_triples += 1
    obs = x.parse("Synthetic_Observations")
    n_obs = 0
    for _, r in obs.iterrows():
        o = INST[str(r["obs_id"])]
        g.add((o, RDF.type, CMPO.CMPObservation))
        g.add((o, SOSA.observedProperty, term(r["sosa:observedProperty"])))
        g.add((o, SOSA.hasFeatureOfInterest, INST[str(r["sosa:hasFeatureOfInterest"])]))
        link_p = CMPO.madeOnPlatform if "Platform" in str(r["platform/sensor link"]) else SOSA.madeBySensor
        g.add((o, link_p, INST[str(r["link target"])]))
        if pd.notna(r.get("cmpo:duringStep")):
            g.add((o, CMPO.duringStep, INST[str(r["cmpo:duringStep"])]))
        g.add((o, SOSA.hasSimpleResult, Literal(float(r["sosa:hasSimpleResult"]), datatype=XSD.float)))
        if pd.notna(r.get("sosa:resultTime")):
            g.add((o, SOSA.resultTime, Literal(str(r["sosa:resultTime"]), datatype=XSD.dateTime)))
        if pd.notna(r.get("cmpo:rawTimestamp")):
            g.add((o, CMPO.rawTimestamp, Literal(r["cmpo:rawTimestamp"], datatype=XSD.decimal)))
        n_obs += 1
    return {"synthetic_entity_triples": n_ent_triples, "synthetic_observations": n_obs}


def main():
    t0 = time.time()
    print("Stage 1: profiling")
    prof = stage1_profile()
    for f, p in prof.items():
        print(f"  {f}: {p['rows']} rows x {p['n_columns']} cols, missing cells {p['missing_cells']}")
    print("Stage 2: alignment (mapping spec)")
    rows, meas = stage2_alignment()
    print(f"  mapping rows: {len(rows)}; measurement columns: {len(meas)}")
    print("Stage 3+4: normalization + RDF generation")
    g, stats = stage34_generate(meas)
    print(f"  observations: {stats['observations']}, skipped missing cells: {stats['cells_skipped_missing']}")
    synth = stage_synth(g)
    print(f"  synthetic: {synth}")
    print(f"  graph: {len(g)} triples")
    g.serialize(OUT / "kg_unvalidated.ttl", format="turtle")
    stats.update(synth); stats["triples"] = len(g)
    stats["runtime_s"] = round(time.time() - t0, 1)
    (OUT / "generation_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"done in {stats['runtime_s']}s -> {OUT}/kg_unvalidated.ttl")


if __name__ == "__main__":
    main()
