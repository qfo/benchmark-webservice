#!/usr/bin/env python
import os
import subprocess

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


BASEURLS = {
        "2022.1": "https://zenodo.org/records/10517603/files/",
        "2022.0": "https://zenodo.org/records/7919753/files/",
        "2020.2": "https://zenodo.org/records/15087752/files/",
        "2018": "https://zenodo.org/records/15087679/files/",
        "2011": "https://zenodo.org/records/15083829/files/",
}
BASEURLS["2022"] = BASEURLS["2022.1"]
BASEURLS["2020"] = BASEURLS["2020.2"]


def get_file_list(release):
    if release not in BASEURLS:
        raise KeyError(f"Either release {release} is unknown, or a base URL is not available for it yet")
    files = [
       'Summaries.drw.gz',
       'GOdata.drw.gz',
       'mapping.json.gz',
       'ServerIndexed.db',
       'ServerIndexed.db.map',
       'ServerIndexed.db.tree',
       'enzymes.drw.gz',
       'ReconciledTrees_SwissTrees.drw',
       'ReconciledTrees_TreeFam-A.drw',
       'TreeCat_Euk.drw',
       'TreeCat_Bac.drw',
       'TreeCat_Fun.drw']
    if int(release.split('.')[0]) <= 2020:
        files.extend([
            'speciestree_Luca_conf81.drw',
            'speciestree_Euk_conf81.drw',
            'speciestree_Ver_conf81.drw',
            'speciestree_Fun_conf81.drw',
        ])
    if int(release.split('.')[0]) >= 2011:
        files.extend([
            'lineage_tree.phyloxml',
            'species_tree_samples_Luca.nwk',
            'species_tree_samples_Ver.nwk',
            'species_tree_samples_Euk.nwk',
            'species_tree_samples_Fun.nwk'])
    if int(release.split('.')[0]) >= 2020:
        files.extend([
            'vgnc-orthologs.txt.gz',
            'swissprot.txt.gz',
            'fas_precomputed.json.gz',
            'fas_annotations.tgz',
        ])
    return [os.path.join(BASEURLS[release], f) for f in files]


def retrieve_files(files, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for url in files:
        fname = os.path.basename(url)
        target = os.path.join(target_dir, fname)
        urlretrieve(url, target)
        if fname.endswith('.tgz'):
            subprocess.run(['tar', 'xzf', fname], cwd=target_dir, check=True)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Download reference data of a given release "
                                            "for the QfO benchmarking platform")
    p.add_argument('release', choices=("2011", "2018", "2019", "2020", "2020.1", "2020.2", "2022", "2022.1"),
                   help="release version to download. Note that the pure year release always points to the latest"
                        "version of that year (e.g. 2020 --> 2020.2"
                   )
    p.add_argument('--out-dir', help="directory where to store the data. Defaults to ./reference_data/<release>")

    conf = p.parse_args()
    if conf.out_dir is None:
        conf.out_dir = os.path.join("reference_data", str(conf.release))

    retrieve_files(get_file_list(conf.release), conf.out_dir)
    print("Finished downloading data for release {}. Stored in {}".format(conf.release, conf.out_dir))

