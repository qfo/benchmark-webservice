#!/usr/bin/env python
import os

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


BASEURL = "https://orthology.benchmarkservice.org/refsets"


def get_file_list(release):
    files = [
       'Summaries.drw.gz',
       'GOdata.drw.gz',
       'mapping.json.gz',
       'ServerIndexed.db',
       'ServerIndexed.db.map',
       'ServerIndexed.db.tree',
       'enzymes.drw.gz',
       'speciestree_Luca_conf81.drw',
       'speciestree_Euk_conf81.drw',
       'speciestree_Ver_conf81.drw',
       'speciestree_Fun_conf81.drw',
       'ReconciledTrees_SwissTrees.drw',
       'ReconciledTrees_TreeFam-A.drw',
       'TreeCat_Euk.drw',
       'TreeCat_Bac.drw',
       'TreeCat_Fun.drw']
    if release > 2011:
        files.extend([
            'lineage_tree.phyloxml',
            'tree_samples_Luca.nwk',
            'tree_samples_Ver.nwk',
            'tree_samples_Euk.nwk',
            'tree_samples_Fun.nwk'])
    return [os.path.join(BASEURL, str(release), f) for f in files]


def retrieve_files(files, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for url in files:
        fname = os.path.basename(url)
        target = os.path.join(target_dir, fname)
        urlretrieve(url, target)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Download reference data of a given release for the QfO benchmarking platform")
    p.add_argument('release', choices=(2011,2018,2019), type=int, help="release version to download")
    p.add_argument('--out-dir', help="directory where to store the data. Defaults to ./reference_data/<release>")

    conf = p.parse_args()
    if conf.out_dir is None:
        conf.out_dir = os.path.join("reference_data", str(conf.release))

    retrieve_files(get_file_list(conf.release), conf.out_dir)
    print("Finished downloading data for release {}. Stored in {}".format(conf.release, conf.out_dir))


