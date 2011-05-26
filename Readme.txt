Update Steps after Changeing the OMA-Release
============================================

- backup data/projectKeys.drw data/GenomeStarts.drw data/enzymes.drw
  data/TreeCat_* data/ReconciledTrees.drw, data/testProperies.drw

- Add new OMA DB to projectsKeys (adjust old values)
- Adjust lib/darwinit: 
  - path to brwrel;
- update data/* 

- Start Server and
  - call RedoProjectMapping of public databases in the Browser, e.g.
    ?f=RedoProjectMapping&p1='/local/BenchmarkService/projects/Ensembl_56.589'&p2=Ensembl+56&p3=<nr_seqs>&p4=<nr_orth>

  - adjust public-flag and restart service.

