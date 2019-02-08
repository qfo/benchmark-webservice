#!/usr/bin/env python

import requests
import bs4
import tarfile
import shutil
import os
import re


def load_html(url):
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.content, 'html.parser')
    return soup


def get_benchmark_divs(soup):
    return soup.find_all('div', id=True, class_="carousel")


def download_file(url):
    local_filename = "/tmp/" + url.split('/')[-1]
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as fh:
        shutil.copyfileobj(r.raw, fh)
    return local_filename


def extract_gnuplot_data_file(lnk, target_name):
    folder, fname = os.path.split(target_name)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    tgz_fname = download_file(lnk)
    with tarfile.open(tgz_fname, mode='r') as tar:
        obj = [x for x in tar.getmembers() if x.name.endswith('.dat')]
        assert(len(obj) == 1)
        tar.extractall(folder, members=obj)
    os.rename(os.path.join(folder, obj[0].name), os.path.join(folder, fname))
    os.remove(tgz_fname)


def divname_to_bsclass(name):
    if "Generalized" in name:
        idx = name.index('Generalized')
        return "STD_Generalized", name[:idx]
    elif "ReferenceGene" in name:
        return "SwissTree", "SwissTree"
    elif "Semi-auto" in name:
        return "TreeFam-A", "TreeFam-A"
    elif "Tree" in name:
        idx = name.index('Tree')
        return "STD", name[:idx]
    elif "GeneOntology" in name:
        return "GO", "GOConservation"
    elif "EnzymeClass" in name:
        return "EC", "ECConservation"


def get_benchmark_data(div, root):
    name = div.get('id')
    lnks = div.find_all('a', string=re.compile(r".*Gnuplot.*"))
    res_names = ['_RF_trees', '_frac-wrong_tree', '_RF_nr-orthologs', '_frac-wrong_nr-orthologs'] if len(lnks)>1 else ['']
    for ext, link_tag in zip(res_names, lnks):
        class_, base = divname_to_bsclass(name)
        link = "https://orthology.benchmarkservice.org" + link_tag.get('href')
        extract_gnuplot_data_file(link, "dump/{}/{}/{}{}.dat".format(root, class_, base, ext))


def run(url, root):
    doc = load_html(url)
    for div in get_benchmark_divs(doc):
        get_benchmark_data(div, root)


if __name__ == "__main__":
    run('https://orthology.benchmarkservice.org/cgi-bin/gateway.pl?f=CheckResults&p1=72d29d4aebb02e0d396fcad2', 'RefSet_2011')
    run('https://orthology.benchmarkservice.org/cgi-bin/gateway.pl?f=CheckResults&p1=c6f7dc6125f3686d68e1e938', 'RefSet_2017')
    run('https://orthology.benchmarkservice.org/cgi-bin/gateway.pl?f=CheckResults&p1=10f28e6c09fd6acc1a90ade6', 'RefSet_2018')
