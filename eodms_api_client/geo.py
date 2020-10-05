import geopandas as gpd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape

SRC_CRS = CRS('epsg:4326')

def transform_metadata_geometry(meta_geom, target_crs=None):
    '''
    EODMS always returns geometries in WGS84, so we provide the option to transform
    into something more useful through the use of a CLI flag (--t_srs)
    '''
    meta_geom = shape(meta_geom)
    if target_crs is None:
        return meta_geom
    dst_crs = CRS(target_crs)
    trans = Transformer.from_crs(
        crs_from=SRC_CRS,
        crs_to=dst_crs,
        always_xy=True
    )
    lons, lats = meta_geom.exterior.coords.xy
    xs, ys = trans.transform(xx=lons, yy=lats)
    return Polygon(zip(xs, ys))

def metadata_to_gdf(metadata, target_crs=None):
    df = gpd.GeoDataFrame()

def load_search_aoi(geofile):
    pass
