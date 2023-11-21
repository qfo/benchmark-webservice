Quest for Orthologs benchmarking with OpenEBench
================================================

Quest for Orthologs (QfO) Benchmark pipeline with Nextflow and Docker. This branch of the
repository contains the development implementation for running the QfO benchmarking
http://orthology.benchmark-service.org on the OpenEBench platform. The codebase is by no
means stable nor bug free.


Description
-----------

The workflow takes as input the ortholog predictions of a method in
either tab-delimited format that lists pairs of orthologs or an
orthoxml file. The predictions must be done on the QfO reference proteomes, either
on the dataset of 2011 or 2018. For how to retrieve the reference proteomes, please
consider the instructions on the current `benchmark service`_. The workflow will
(i) validate the input predictions, (ii) convert the predictions into an internal format,
and (iii) compute the benchmark metrics for various benchmarks.


Data
----
Orthology predictions must be provided by the user. An example file is available in the
example directory. Reference datasets have to be made available to the workflow
and can be obtained online for the publicly accessible datasets. See Usage section
for more details how to obtain them.

Usage
-----

 #. You must have a running installation of Docker_ and Nextflow_.

 #. Clone this repository

 #. ~~Create the necessary docker images by running ``./build_dockers.sh latest``~~
    This is no longer needed, as the nextflow.config contains the docker tags in the
    container specification and will download the relevant image from dockerhub
    automatically.

 #. Download the reference data by running ``./fetch_reference_data.py``. for the
    desired year. This will download the reference datasets for the store
    them in reference_data/<year>/. The nextflow workflow can then mount the data
    into the docker container.

 #. Run the pipeline with ``nextflow run main.nf -profile docker``

this will launch the pipeline with the default parameters that are specified in the
`nextflow config`_ file. Output files will be created by default into ``out/``.
Use ``nextflow run main.nf --help`` to obtain a list of possible parameters.

.. _Docker: https://www.docker.com
.. _Nextflow: https://www.nextflow.io
.. _benchmark service: https://orthology.benchmark-service.org
.. _nextflow config: nextflow.config


