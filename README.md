# EODMS API Client

A Python3 package for querying and ordering from the REST API provided by Natural Resources Canada's [Earth Observation Data Management System (EODMS)](https://www.eodms-sgdot.nrcan-rncan.gc.ca/index_en.jsp).

**Currently only works for RCMImageProducts collection**

Heavily influenced by the utterly fantastic `sentinelsat` package: https://github.com/sentinelsat/sentinelsat

## Usage:

### CLI

Given a geojson polygon, query (but do not order) the RCM collection for products in the last 24hrs and dump the results to a geojson file for inspection (`query_results.geojson`)

```
$ eodms -c RCMImageProducts -g query_aoi.geojson --dump-results
```

Same query as above, but this time submit an order for all products found by the query instead of saving a result file

```
$ eodms -c RCMImageProducts -g query_aoi.geojson --submit-order
```

### Interactive Python

Repeating the same query as the CLI example above in a Python REPL allows you to manually inspect the results and do all sorts of interesting things with the query result geodataframe. 

For example, one may wish to inspect the image metadata to check approximate download sizes. One may also want to inspect the image footprints to ensure that they are ordering only the images which have most-optimal coverage of their `query_aoi.geojson` polygon.

```
>>> from eodms_api_client import EodmsAPI
>>> x = EodmsAPI(collection='RCMImageProducts')
>>> x.query(geometry='query_aoi.geojson')
>>> type(x.results)
geopandas.geodataframe.GeoDataFrame
```

### List of possible CLI arguments

```
$ eodms --help
Usage: eodms [OPTIONS]

Options:
  -u, --username TEXT             EODMS username (leave blank to use .netrc or
                                  be prompted)
  -p, --password TEXT             EODMS password (leave blank to use .netrc or
                                  be prompted)
  -c, --collection [Radarsat|Radarsat2|RCMImageProducts|NAPL|PlanetScope]
                                  EODMS collection to search  [required]
  -s, --start TEXT                Beginning of acquisition time window
                                  (default to 1 day prior to now)
  -e, --end TEXT                  End of acquisition time window (default to
                                  now)
  -g, --geometry PATH             File containing polygon used to constrain
                                  the query results to a spatial region
  -pt, --product-type TEXT        Limit results to a certain image product
                                  type
  -pf, --product-format [GeoTIFF|NITF21]
                                  Limit results to a certain image product
                                  format
  -rel, --relative-orbit TEXT     Limit results to the desired relative orbit
                                  Id
  -abs, --absolute-orbit TEXT     Limit results to the desired absolute orbit
                                  Id
  -ia, --incidence-angle TEXT     Limit results to the desired incidence angle
  -rb, --radarsat-beam-mode TEXT  Limit SAR collection results to the desired
                                  beam mode
  -rm, --radarsat-beam-mnemonic TEXT
                                  Limit SAR collection results to the desired
                                  beam mnemonic
  -rp, --radarsat-polarization [CH+CV|HH|HH+HV|HH+HV+VH+VV|HH+VV|HV|VH|VH+VV|VV]
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
  --dump-results                  Whether or not to create a geopackage
                                  containing the results of the query
  --submit-order                  Submit an order to EODMS from the results of
                                  the current query parameters
  --record-id TEXT                Specific record_Id to order from the desired
                                  collection
  --record-ids PATH               File of line-separated record_Ids to order
                                  from the desired collection
  --download-ids PATH             File of line-separated itemIds to download
                                  from EODMS
  --download-dir PATH             Directory for downloaded files
  --log-verbose                   Use debug-level logging
  -h, --help                      Show this message and exit.
```

## ToDo:

- [x] query RCM
- [x] query and order RCM
- [x] order with provided record Ids (no query necessary)
- [x] download given item Ids (no query or order submission necessary)
- [ ] blindly order (no metadata fetching, just order whatever is returned by query)
- [ ] add support for other collections:
  - [x] Radarsat2 (*WIP*)
  - [ ] Radarsat
  - [ ] PlanetScope
- [ ] add multi-select functionality for supported collection parameters
- [ ] allow for collection-switching for an existing EodmsAPI instance (must re-evaluate params and rebuild search_url)
- [ ] readthedocs documentation?
