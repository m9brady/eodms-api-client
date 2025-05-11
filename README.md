# EODMS API Client

[![Conda (channel only)](https://img.shields.io/conda/vn/conda-forge/eodms-api-client)](https://anaconda.org/conda-forge/eodms-api-client)
[![PyPI](https://img.shields.io/pypi/v/eodms-api-client)](https://pypi.org/project/eodms-api-client)
[![Documentation](https://github.com/m9brady/eodms-api-client/actions/workflows/pages/pages-build-deployment/badge.svg?branch=gh-pages)](https://m9brady.github.io/eodms-api-client/)

A Python3 package for querying, ordering and downloading from the REST API provided by Natural Resources Canada's [Earth Observation Data Management System (EODMS)](https://www.eodms-sgdot.nrcan-rncan.gc.ca/index_en.jsp).

Heavily influenced by the utterly fantastic `sentinelsat` package: https://github.com/sentinelsat/sentinelsat

## Usage:

Full documentation and real-world example on [GitHub Pages](https://m9brady.github.io/eodms-api-client/)!

## Quickstart:

Create a new environment with [conda](https://docs.conda.io/en/latest/miniconda.html)

```console
conda create -n eodms-env eodms-api-client -c conda-forge
conda activate eodms-env
```

... or install with pip
> **Warning**
> Pip is not recommended
> - may clobber your existing Python environment
> - may be problematic with Windows+GDAL

```console
pip install eodms-api-client
```

### Use the CLI

Given a geojson file containing search geometry (Point, Line, Polygon), query - but do not order - the RCM collection for products in the last 24hrs and dump the results to a geojson file for inspection (`query_results.geojson`)

```console
eodms -c RCM -g query_aoi.geojson --dump-results
```

Same query as above, but this time submit an order for all products found by the query instead of saving a result file

```console
eodms -c RCM -g query_aoi.geojson --submit-order
```

After submitting an order, this package will return a list of Order IDs that users should take note of as these will be used to download the imagery once the order is complete:

```console
eodms -c RCM --order-id [integer Order ID]
```

If your order produced several Order IDs (e.g. more than 50 images ordered at once), you may wish to create a text file of line-separated Order IDs to feed to the package:

```console
eodms -c RCM --order-ids [path to text file containing integer Order IDs]
```

### Use interactively in a Python REPL

Repeating the same query as the CLI example above in a Python REPL allows you to manually inspect the results and do all sorts of interesting things with the query result geodataframe. 

For example, one may wish to inspect the image metadata to check approximate download sizes. One may also want to inspect the image footprints to ensure that they are ordering only the images which have most-optimal coverage of their `query_aoi.geojson`.

```python
>>> from eodms_api_client import EodmsAPI
>>> x = EodmsAPI(collection='RCM')
>>> x.query(geometry='query_aoi.geojson')
>>> type(x.results)
geopandas.geodataframe.GeoDataFrame
```

### List of possible CLI arguments

```console
eodms --help
Usage: eodms [OPTIONS]

Options:
  -u, --username TEXT             EODMS username (leave blank to use .netrc or
                                  be prompted)

  -p, --password TEXT             EODMS password (leave blank to use .netrc or
                                  be prompted)

  -c, --collection TEXT           EODMS collection to search  [required]

  -s, --start TEXT                Beginning of acquisition time window
                                  (default to 1 day prior to now)

  -e, --end TEXT                  End of acquisition time window (default to
                                  now)

  -g, --geometry PATH             File containing vector feature(s) used to
                                  constrain the query results to a spatial
                                  region

  -pt, --product-type TEXT        Limit results to a certain image product
                                  type

  -pf, --product-format [GeoTIFF|NITF21]
                                  Limit results to a certain image product
                                  format

  -sr, --spatial-resolution TEXT  Limit results to the desired spatial
                                  resolution

  -rel, --relative-orbit TEXT     Limit results to the desired relative orbit
                                  Id

  -abs, --absolute-orbit TEXT     Limit results to the desired absolute orbit
                                  Id

  -ia, --incidence-angle TEXT     Limit results to the desired incidence angle

  -ial, --incidence-angle-low TEXT
                                  Limit results to scenes that have incidence
                                  angles greater than this value (degrees)

  -iah, --incidence-angle-high TEXT
                                  Limit results to scenes that have incidence
                                  angles less than this value (degrees)

  -rb, --radarsat-beam-mode TEXT  Limit SAR collection results to the desired
                                  beam mode

  -rm, --radarsat-beam-mnemonic TEXT
                                  Limit SAR collection results to the desired
                                  beam mnemonic

  -rp, --radarsat-polarization [CH CV|HH|HH HV|HH HV VH VV|HH VV|HV|VH|VH VV|VV]
                                  Limit SAR collection results to the desired
                                  polarization

  -ro, --radarsat-orbit-direction [Ascending|Descending]
                                  Limit SAR collection results to the desired
                                  orbit type

  -rl, --radarsat-look-direction [Left|Right]
                                  Limit SAR collection results to the desired
                                  antenna look direction

  -rd, --radarsat-downlink-segment-id TEXT
                                  Limit SAR collection results to the desired
                                  downlink segment Id

  -rs, --rcm-satellite [RCM1|RCM2|RCM3]
                                  Limit RCM collection results to the desired
                                  satellite

  -cc, --cloud-cover TEXT         Limit optical results to have less than this
                                  amount of cloud cover [0-100]

  -rn, --roll-number TEXT         Limit NAPL results to the given roll number

  -pn, --photo-number TEXT        Limit NAPL results to the given photo number

  --priority [Low|Medium|High|Urgent]
                                  What priority to use when submitting orders
                                  [default: Medium]

  -o, --output-dir DIRECTORY      Directory where query results and downloaded
                                  imagery will be saved  [default: .]

  -dr, --dump-results             Whether or not to create a geojson dump
                                  containing the results of the query

  -dfn, --dump-filename TEXT      Filename for query results geojson
                                  [default: query_results]

  --submit-order                  Submit an order to EODMS from the results of
                                  the current query parameters

  --record-id INTEGER             Specific Record Id to order from the desired
                                  collection

  --record-ids PATH               File of line-separated Record Ids to order
                                  from the desired collection

  --order-id INTEGER              Specific Order Id to download from EODMS

  --order-ids PATH                File of line-separated Order Ids to download
                                  from EODMS

  --uuid TEXT                     Specific UUID to order from the desired
                                  collection

  --uuid-list PATH                File of line-separated UUIDs to order from
                                  the desired collection
                                  
  --n-dds-workers INTEGER         Number of concurrent threads to use when
                                  downloading from DDS api

  --verbose                       Use debug-level logging

  --version                       Show the package version

  -h, --help                      Show this message and exit.

```

## ToDo:

- [x] query RCM
- [x] query and order RCM
- [x] order with provided record Ids (no query necessary)
- [x] download given item Ids (no query or order submission necessary)
- [ ] blindly order (skip extra metadata fetching, just order whatever is returned by query)
- [x] add support for other collections:
  - [x] Radarsat2 (*WIP*)
  - [x] Radarsat1 (*WIP*)
  - [x] PlanetScope (*WIP*)
- [ ] add multi-select functionality for supported collection parameters
- [x] allow for collection-switching for an existing EodmsAPI instance (must re-evaluate params and rebuild search_url)
- [x] readthedocs documentation
