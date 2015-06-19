Orthology-Benchmarking-Webservice
=================================

This repository contains the codebase that runs the webservice 
to benchmark orthology predictions on a common reference proteome 
dataset. The webservice is available for public usage at 
http://orthology.benchmark-service.org

This codebase is primarly intendent for as an implementation 
reference and for people interested in providing 
additional benchmarks. 


Installation
------------
If you intend to run your own instance of the webservice, here is 
what you need to do. The service is designed to be run on a 
ubuntu machine, but other linux systems should be ok as well 
(although you might need to change some packages, paths, etc).

Before anything else, clone the repository on your dev machine and 
deploy everything from there.

 1. Setup Host/VM

    Along in this repostitory there comes a `cdist`_ installation configuration, 
    that configures a bare-bone ubuntu server. You must have root access 
    to the machine in order to use it. After adding your ssh public key to 
    .cdist/manifest/ssh/ execute cdist from the 
    root directory of the repository like this:
       
       cdist config --conf-dir .cdist <host>

 2. Deploy webservice to the web server. 

    use the deploy script to setup the host:
    
      ./deploy cbrg-obs@<host> <path/to/dataroot>
    
    make sure that the <path/to/dataroot> directory exists and that the user 
    cbrg-obs has read-write access to it.

 
 3. The service should be running...

.. _cdist: http://www.nico.schottelius.org/software/cdist/


