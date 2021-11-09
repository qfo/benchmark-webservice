import itertools
import logging
import gzip
import json

logger = logging.getLogger("hgnc-convert")


def extract_rels_from_line(line, refset_data):
    symbol, *genes = line.strip().split("\t")
    acc_per_gene = []
    for gene in genes:
        up_ids = gene.rsplit("#", 1)[1].split("|")
        mapped = list(filter(lambda x: x is not None,
                             (refset_data['mapping'].get(up, None) for up in up_ids)))
        if len(mapped) > 1:
            logger.warning(f"{symbol}: gene {gene} with {len(up_ids)} uniprot acc maps to several "
                           f"different proteins: {mapped}. Excluding this gene")
        elif len(mapped) == 1:
            acc_per_gene.append(mapped[0])
    logger.debug(f"{symbol}: {acc_per_gene} --> {len(acc_per_gene)*(len(acc_per_gene)-1)/2} relations")
    for rel in itertools.combinations(acc_per_gene, 2):
        yield rel, symbol


def extract_and_write_hgnc_orthologs(hgnc_dump, refset_data, out_fh):
    open_ = gzip.open if hgnc_dump.endswith(".gz") else open
    with open_(hgnc_dump, 'rt') as hgnc_fh:
        for line in hgnc_fh:
            for rel, symbol in extract_rels_from_line(line, refset_data):
                out_fh.write(f"{rel[0]}\t{rel[1]}\t{symbol}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Refset relevant orthologs relations asserted from HGNC")
    parser.add_argument('--hgnc-dump',
                        help="tab-separated dump file from HGNC")
    parser.add_argument('--mapping',
                        help="mapping json file for reference dataset")
    parser.add_argument('--out', default="output file path")
    parser.add_argument('-v', action='count', default=0,
                        help="increase verbosity of program. add -vv for debug level")
    conf = parser.parse_args()
    logging.basicConfig(level=30 - 10 * min(conf.v, 2),
                        format='%(asctime)-15s %(name)s %(levelname)-8s: %(message)s')
    logger.info(str(conf))

    with gzip.open(conf.mapping, 'rt') as fh:
        refset_data = json.load(fh)

    with gzip.open(conf.out, 'wt') as fh:
        extract_and_write_hgnc_orthologs(conf.hgnc_dump, refset_data, fh)


