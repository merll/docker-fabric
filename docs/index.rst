.. Docker-Fabric documentation master file, created by
   sphinx-quickstart on Tue Sep  2 07:43:06 2014.

Welcome to Docker-Fabric's documentation!
=========================================

Docker-Fabric provides a set of utilities for controlling Docker on a local test machine or a remote production
environment. It combines Fabric_ with extensions to docker-py_ in Docker-Map_.

The project is hosted on GitHub_.


Features
========
* Integration of docker-map's container structure into Fabric deployments.
* Complements Docker API commands with command line shortcuts, where appropriate.
* Use Fabric's SSH tunnel for connecting to the Docker Remote API.
* Fabric-like console feedback for Docker image and container management.


Contents
========

.. toctree::
   :maxdepth: 2

   installation
   start
   api/modules


Status
======
Docker-Fabric is being used for small-scale deployment scenarios in test and production. It should currently considered
beta, due to pending new features, generalizations, and unit tests.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _Fabric: http://www.fabfile.org
.. _docker-py: https://github.com/docker/docker-py
.. _Docker-Map: https://github.com/merll/docker-map
.. _GitHub: https://github.com/merll/docker-fabric
