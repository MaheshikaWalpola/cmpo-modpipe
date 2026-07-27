# Provenance of the portal study

Every artifact in this folder comes from one of two repositories. The relevant
source is quoted here in full, because one of those repositories is being taken
private and the paper's claims must remain checkable from this repository
alone.

## The two portals

**KGPortal** — `https://github.com/MaheshikaWalpola/KGPortal`, commit
`0a79c0da02bc1cc4bd29cb0bf5c54884f6c444de` (2026-06-08). The earlier
deployment. This is the snapshot the E0 audit in `legacy_audit/` runs against;
it holds `ontology/Schema.ttl`, `ontology/Instances.ttl` and
`SHACL/cmpo_shapes.ttl`, the three inputs `legacy_audit/run_evaluation.py`
expects. It remains public.

**KGtest** — the current portal, commit
`2785ad06bef329075a0d1968a875c608c4ec219c` (2026-07-27), 147 commits from
2026-03-03. This is where the three portal runs in `runs/` were generated. It
is being taken private, so the code the paper's E4 section describes is quoted
below rather than linked.

## The E0 shape suite

`KGPortal/SHACL/cmpo_shapes.ttl` declares nine node shapes, targeting
`cmpo:Wafer`, `cmpo:CMPTool`, `cmpo:Recipe`, `cmpo:Slurry`,
`cmpo:PolishingPad`, `cmpo:Pressure`, `cmpo:PlatenSpeed`, `cmpo:CMPProcess`
and `cmpo:Lot`. `legacy_audit/results.json` records five of those nine as
targeting classes with zero asserted instances: `CMPProcess`, `CMPTool`,
`PlatenSpeed`, `Pressure` and `Slurry`. Both causes named in the paper are
visible in the file itself — every value constraint is written against
`cmpo:hasNumericValue`, and every shape targets a parent class while the
generator types instances with subclasses.

## The generation code

One model call per statement, merged by parsing each fragment. From
`backend/services/validation_service.py`,
`ValidationService.generate_shacl_shapes_stream`:

```python
with ThreadPoolExecutor(max_workers=min(len(rules), 10)) as executor:
    tasks = [
        loop.run_in_executor(executor, generate_single_shape, i, rule)
        for i, rule in enumerate(rules)
    ]
    for future in asyncio.as_completed(tasks):
        res = await future
        if res["status"] == "success":
            completed_shapes[res["index"]] = res["shacl"]
        ...

# Merge all shapes into a final RDF graph to prettify and deduplicate prefixes
if completed_shapes:
    g = Graph()
    for idx in sorted(completed_shapes.keys()):
        chunk = completed_shapes[idx]
        try:
            g.parse(data=chunk, format="turtle")
        except Exception as parse_err:
            print(f"rdflib failed to parse chunk {idx}: {parse_err}. ...")
```

A fragment that fails to parse is printed to the server console and dropped.
It is not re-raised, not surfaced to the client, and not counted. This is the
mechanism behind the three to five statements missing from each run.

The per-statement prompt instructs the model to name each shape
`inst:Question_{index+1}_Shape` **"or similar"**. Every run took that licence
for exactly one statement, emitting `inst:Tool_Identifier_Shape` for statement
9. The prompt also carries a single worked example — a `sh:NodeShape` with one
nested `sh:property` block — which is the only constraint pattern demonstrated.

Sampling temperature is `0.1` for shape generation and `0.2` for the
statement-suggestion step; the default elsewhere in the service is `0.7`. It is
not zero, which is why three runs of the same twenty statements against the
same schema produced three different suites.

## The inference endpoint

Despite the file being named `local_llm_service.py`, the service is not local.
It posts to an OpenAI-compatible chat-completions endpoint configured by
environment variables:

```python
KISTE_API_URL = os.getenv("KISTE_API_URL")
KISTE_API_KEY = os.getenv("KISTE_API_KEY")
MODEL_NAME    = os.getenv("KISTE_MODEL")  # "gpt-oss-120b" or "qwen3.6"
```

The model is therefore whatever `KISTE_MODEL` was set to at the time of a run,
and that value was not recorded alongside the runs. The paper states this
rather than naming a model.

## The pass-counting defect

From the same file, the report builds its rule list from node shapes and from
subjects of `sh:targetClass`:

```python
shape_nodes_set = set(g_shapes.subjects(RDF.type, SH.NodeShape)).union(
    set(g_shapes.subjects(RDF.type, SH.PropertyShape)))
for s in g_shapes.subjects(SH.targetClass, None):
    shape_nodes_set.add(s)
```

and scores each entry from the focus nodes recorded against it:

```python
source_shape = results_graph.value(result_node, SH.sourceShape)
...
failed_nodes = shape_failed_nodes.get(shape_str, set())
passed = (failed_items_count == 0) and (shape_str not in violated_shapes)
```

`sh:sourceShape` names the *property* shape, which in generated output is an
anonymous blank node and is never a member of `shape_nodes_set`. Every named
rule therefore keeps an empty failure set and is scored as passed, however many
violations the run produced. `check_shapes.py` resolves the property shape back
to its owning node shape before scoring, which is the fix.

## The ontology-drafting prompts

`KGPortal/Prompts/ontology_elicitation.md` and
`Prompts/explanation_generation.md` are released with that repository and
remain public. They must not be read as a prompt log. The first file states in
its own closing note:

> These prompts are not exact transcripts. They are written to give a
> conceptual idea of how the ontology was developed conversationally with an AI
> assistant. In practice, the process was exploratory.

An earlier revision of that file named a specific model and date. It was
replaced by the disclaimer above, so no model name or date is claimed for the
ontology drafting anywhere in the paper or in `CONSTRUCTION_HISTORY.md`. The
generation prompts quoted in this document are different in kind: they are
literal string constants in version-controlled source, not reconstructions.

## The data graph behind the exported report

The portal report quoted in `README.md` was produced against a
796,900-triple instance graph generated inside the portal workspace, not
against `kg/kg_cmpo_v2.1.ttl` (252,873 triples). Its 424 + 424 timestamp
findings correspond to the 424 removal-rate rows of the full PHM 2016 test
set, whereas the released graph covers one file pair with four wafers. The two
are reported separately and never compared row by row.
