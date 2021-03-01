from os.path import splitext

import fiona
import geopandas as gpd
import pandas as pd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.wkt import dumps as to_wkt

# add 'read' support for KML/KMZ - disabled by default
fiona.drvsupport.supported_drivers['KML'] = 'r'

SRC_CRS = CRS('epsg:4326')

def transform_metadata_geometry(meta_geom, target_crs=None):
    '''
    Transform a given image footprint geometry from WGS84 to the desired crs

    EODMS always returns geometries in WGS84, so we provide the option to transform
    into something more useful through the use of a CLI flag (--t_srs)

    Inputs:
      - meta_geom: the footprint geometry as a shapely.geometry object
      - target_crs: either a pyproj.CRS or properly-formatted string for the desired projection

    Outputs:
      - if target_crs is not supplied, simply return the passed geometry
      - if target_crs is supplied, return the transformed geometry
    '''
    meta_geom = shape(meta_geom)
    if target_crs is None:
        return meta_geom
    elif isinstance(target_crs, CRS):
        dst_crs = target_crs
    else:
        dst_crs = CRS(target_crs)
    trans = Transformer.from_crs(
        crs_from=SRC_CRS,
        crs_to=dst_crs,
        always_xy=True
    )
    lons, lats = meta_geom.exterior.coords.xy
    xs, ys = trans.transform(xx=lons, yy=lats)
    return Polygon(zip(xs, ys))

def metadata_to_gdf(metadata, collection, target_crs=None):
    '''
    Instead of a jumbled JSON-looking dictionary, create a geopandas.GeoDataFrame from the 
    EODMS search query response

    Inputs:
      - metadata: dictionary of EODMS search query and image metadata response
      - collection: string of EODMS Collection ID - used for column name standardization
      - target_crs: pyproj.CRS instance or properly-formatted string for the desired projection

    Outputs:
      - df: geopandas.GeoDataFrame containing <metadata> projected to <target_crs>
    '''
    if target_crs is None:
        crs = CRS('epsg:4326')
    elif isinstance(target_crs, CRS):
        crs = target_crs
    else:
        crs = CRS(target_crs)
    df = gpd.GeoDataFrame(metadata, crs=crs)
    # standardize some column names
    if collection == 'RCMImageProducts':
        df.rename(
            {
                'recordId': 'EODMS RecordId',
                'title': 'Granule'
            },
            axis=1,
            inplace=True
        )
        date_cols = ['Acquisition Start Date', 'Acquisition End Date']
    elif collection == 'Radarsat2':
        df.rename(
            {
                'Sequence Id': 'EODMS RecordId',
                'Supplier Order Number': 'Granule'
            },
            axis=1,
            inplace=True
        )
        date_cols = ['Start Date', 'End Date']
    elif collection == 'Radarsat1':
        df.rename(
            {
                'Sequence Id': 'EODMS RecordId',
                'Product Id': 'Granule',
                'Start Date': 'End Date', # TODO: Check that this is indeed necessary!
                'End Date': 'Start Date'  # TODO: Check that this is indeed necessary!
            },
            axis=1,
            inplace=True
        )
        # fix column ordering for RS1
        df = df[[
            'EODMS RecordId', 'Granule', 'Start Date', 'End Date', 'Position',
            'Sensor', 'Sensor Mode', 'Beam', 'Polarization', 'Look Orientation',
            'Incidence Angle (Low)', 'Incidence Angle (High)', 'Orbit Direction',
            'Absolute Orbit', 'LUT Applied', 'Product Format', 'Product Type',
            'Spatial Resolution', 'geometry'
        ]]
        date_cols = ['Start Date', 'End Date']
    elif collection == 'PlanetScope':
        df.rename(
            {
                'Sequence Id': 'EODMS RecordId',
                'Title': 'Granule'
            },
            axis=1,
            inplace=True
        )
        date_cols = ['Start Date', 'End Date']
    # convert strings to numeric
    df['EODMS RecordId'] = pd.to_numeric(df['EODMS RecordId'], downcast='integer')
    # convert strings to datetimes
    df[date_cols] = df[date_cols].apply(pd.to_datetime, axis=1)
    # sort by RecordId
    df.sort_values(by='EODMS RecordId', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def load_search_aoi(geofile):
    '''
    Given a file, attempt to parse it as a set of vector features to be sent as part
    of a request to the EODMS REST API. If the features are not already in WGS84, they
    are transformed by this function.

    Inputs:
      - geofile: A file containig vector data (SHP, GEOJSON, GPKG, etc.)

    Outputs:
      - wkt: The Well-Known Text representation of the features within <geofile>
    '''
    # use vsizip for KMZ/Zipped shapefile
    if splitext(geofile)[-1] in ['.kmz', '.zip']:
        df = gpd.read_file(f'/vsizip/{geofile}')
    else:
        df = gpd.read_file(geofile)
    if df.crs != SRC_CRS:
        df = df.to_crs(SRC_CRS)
    geometry = df.unary_union
    if geometry.type == 'MultiPolygon':
        n_vertices = sum([
            len(poly.exterior.coords) - 1
            for poly in geometry
        ])
    elif geometry.type == 'Polygon':
        n_vertices = len(geometry.exterior.coords) - 1
    else:
        raise NotImplementedError('Search geometry must be a polygon/multipolygon')
    if n_vertices > 1000:
        raise Exception('Search geometry is too complex (more than 1000 vertices)')
    wkt = to_wkt(geometry, output_dimension=2) # drop Z dimension if it exists - causes 500-errors with EODMS
    return wkt
