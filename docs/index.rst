eodms-api-client
================

This package was created as a tool for myself for interacting with RCM data archived on the `Earth Observation Data Management System <https://www.eodms-sgdot.nrcan-rncan.gc.ca/index_en.jsp>`__ (EODMS) operated by `Natural Resources Canada <https://www.nrcan.gc.ca/home>`__. 

It provides a command-line interface for querying, ordering, and downloading data from EODMS as well as a Python client class ``EodmsAPI`` for doing the same operations from within a Python session.

.. code-block::

    eodms -c RCM -g aoi_polygon.geojson --dump-results

.. code-block:: python

    >>> from eodms_api_client import EodmsAPI
    >>> client = EodmsAPI(collection='RCM')
    >>> client.query(geometry='aoi_polygon.geojson')

Vector geometry files for spatial subsetting can be anything supported by `Fiona`_ by default (GeoJSON, Esri Shapefile, OGC GeoPackage, KML/KMZ, etc.)

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   examples
   source

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _fiona: https://github.com/Toblerity/Fiona/blob/master/fiona/drvsupport.py
