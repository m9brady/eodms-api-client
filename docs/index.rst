eodms-api-client
================

This package was created as a tool for myself for interacting with RCM data archived on the `Earth Observation Data Management System <https://www.eodms-sgdot.nrcan-rncan.gc.ca/index_en.jsp>`__ (EODMS) operated by `Natural Resources Canada <https://www.nrcan.gc.ca/home>`__. 

It provides a command-line interface for querying, ordering, and downloading data from EODMS as well as a Python client class ``EodmsAPI`` for doing the same operations from within a Python session.

.. code-block:: console

    $ eodms -c RCM -g aoi_polygon.geojson --dump-results

.. code-block:: python

    >>> from eodms_api_client import EodmsAPI
    >>> client = EodmsAPI(collection='RCM')
    >>> client.query(geometry='aoi_polygon.geojson')

Vector geometry files for spatial subsetting can be anything supported by `Fiona`_ (GeoJSON, Esri Shapefile, OGC GeoPackage, KML/KMZ, etc.)

.. tip::
    As of ``v1.3.0`` there is a new RCM data downloading endpoint, accessible from the ``EodmsAPI.download_dds`` method. Read more about it under the examples page: :ref:`dds_example`

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   install
   examples
   source

.. toctree::   
   :caption: Development:

   Github Repository <https://github.com/m9brady/eodms-api-client>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _fiona: https://github.com/Toblerity/Fiona/blob/master/fiona/drvsupport.py
