The PHM 2016 CMP source CSVs are not redistributed here (PHM Society data
challenge terms). To obtain them:

1. Download the 2016 PHM Data Challenge CMP dataset from the PHM Society
   (see the link in the main README).
2. Copy these two files into this data/ directory:
     CMP-test-000.csv        (from CMP-data/test/)
     CMP-test-removalrate.csv
3. Run the pipeline from the repository root:
     python3 modpipe/run_all.py

Everything else in the repository (ontology, shapes, mapping, synthetic
sample, knowledge graph, evaluation results) is committed and needs no
download.
