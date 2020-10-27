# EODMS API Client

A Python3 package for querying and ordering from Natural Resources Canada's Earth Observation Data Management System (EODMS).

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

## ToDo:

- [x] query RCM
- [x] query and order RCM
- [ ] order with provided record Ids (no query necessary)
- [ ] download given order Ids (no query or order submission necessary)
- [ ] blindly order (no metadata fetching, just order whatever is returned by query)
- [ ] add support for other collections (RS2, RS1, PlanetScope first)
- [ ] add multi-select functionality for supported collection arguments
- [ ] allow for collection switching for an existing EodmsAPI instance (must re-evaluate params and rebuild search_url)
- [ ] readthedocs documentation?
