import logging

import click

from . import EodmsAPI

LOGGER = logging.getLogger('eodmsapi.cli')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

@click.command(context_settings={
    'help_option_names': ['-h', '--help']
})
@click.option(
    '--username',
    '-u',
    default=None,
    help='EODMS username (leave blank to use .netrc or be prompted)'
)
@click.option(
    '--password',
    '-p',
    default=None,
    help='EODMS password (leave blank to use .netrc or be prompted)'
)
@click.option(
    '--collection',
    '-c',
    type=click.Choice([
        'Radarsat', 'Radarsat2', 'RCMImageProducts', 'NAPL', 'PlanetScope'
    ], case_sensitive=False),
    required=True,
    help='EODMS collection to search'
)
@click.option(
    '--start',
    '-s',
    default='TODAY-1',
    help='Beginning of acquisition time window (default to 1 day prior to now)'
)
@click.option(
    '--end',
    '-e',
    default='TODAY',
    help='End of acquisition time window (default to now)'
)
@click.option(
    '--geometry',
    '-g',
    type=click.Path(exists=True),
    default=None,
    help='File containing polygon used to constrain the query results to a spatial region'
)
@click.option(
    '--product-type',
    '-pt',
    default=None,
    help='Limit results to a certain image product type'
)
@click.option(
    '--product-format',
    '-pf',
    type=click.Choice(['GeoTIFF', 'NITF21'], case_sensitive=False),
    default=None,
    help='Limit results to a certain image product format'
)
@click.option(
    '--relative-orbit',
    '-rel',
    default=None,
    help='Limit results to the desired relative orbit Id'
)
@click.option(
    '--absolute-orbit',
    '-abs',
    default=None,
    help='Limit results to the desired absolute orbit Id'
)
@click.option(
    '--incidence-angle',
    '-ia',
    default=None,
    help='Limit results to the desired incidence angle' # TODO: why is this not a range in API docs?
)
@click.option(
    '--radarsat-beam-mode',
    '-rb',
    default=None,
    help='Limit SAR collection results to the desired beam mode'
)
@click.option(
    '--radarsat-beam-mnemonic',
    '-rm',
    default=None,
    help='Limit SAR collection results to the desired beam mnemonic'
)
@click.option(
    '--radarsat-polarization',
    '-rp',
    type=click.Choice([
        'CH+CV', 'HH', 'HH+HV', 'HH+HV+VH+VV', 'HH+VV', 'HV', 'VH',
        'VH+VV', 'VV'
    ]),
    default=None,
    help='Limit SAR collection results to the desired polarization'
)
@click.option(
    '--radarsat-orbit-direction',
    '-ro',
    type=click.Choice(['Ascending', 'Descending'], case_sensitive=False),
    default=None,
    help='Limit SAR collection results to the desired orbit type'
)
@click.option(
    '--radarsat-look-direction',
    '-rl',
    type=click.Choice(['Left', 'Right'], case_sensitive=False),
    default=None,
    help='Limit SAR collection results to the desired antenna look direction'
)
@click.option(
    '--radarsat-downlink-segment-id',
    '-rd',
    default=None,
    help='Limit SAR collection results to the desired downlink segment Id'
)
@click.option(
    '--rcm-satellite', # TODO: confirm that this is an undocumented API option
    '-rs',
    type=click.Choice(['RCM1', 'RCM2', 'RCM3']),
    default=None,
    help='Limit RCM collection results to the desired satellite'
)
@click.option(
    '--dump-query',
    is_flag=True,
    default=False,
    help='Whether or not to create a geopackage containing the results of the query'
)
@click.option(
    '--submit-order',
    is_flag=True,
    default=False,
    help='Submit an order to EODMS from the results of the current query parameters'
)
@click.option(
    '--log-verbose',
    is_flag=True,
    default=False,
    help='Use debug-level logging'
)
def cli(
    username,
    password,
    collection,
    start,
    end,
    geometry,
    product_type,
    product_format,
    relative_orbit,
    absolute_orbit,
    incidence_angle,
    radarsat_beam_mode,
    radarsat_beam_mnemonic,
    radarsat_polarization,
    radarsat_orbit_direction,
    radarsat_look_direction,
    radarsat_downlink_segment_id,
    rcm_satellite,
    dump_query,
    submit_order,
    log_verbose
):
    if log_verbose:
        LOGGER.setLevel(logging.DEBUG)
    LOGGER.debug('Connecting to EODMS')
    current = EodmsAPI(collection=collection, username=username, password=password)
    LOGGER.debug('Connected to EODMS')
    LOGGER.info('Querying EODMS API')
    current.query(
        start=start, end=end, geometry=geometry, product_type=product_type,
        product_format=product_format, absolute_orbit=absolute_orbit,
        relative_orbit=relative_orbit, incidence_angle=incidence_angle,
        beam_mode=radarsat_beam_mode, mnemonic=radarsat_beam_mnemonic, 
        polarization=radarsat_polarization, downlink_segment=radarsat_downlink_segment_id,
        orbit_direction=radarsat_orbit_direction,
        look_direction=radarsat_look_direction, rcm_satellite=rcm_satellite,
    )
    LOGGER.info('Finished query. %d result%s' % (
        len(current.results),
        's' if len(current.results) != 1 else ''
    ))
    if dump_query:
        out_file = './query_results.geojson'
        LOGGER.info('Saving query results to file: %s' % out_file)
        current.results.to_file(out_file, driver='GeoJSON')
    if submit_order:
        if len(current.results) > 0:
            LOGGER.info('Submitting order for %d records' % len(current.results))
            record_ids = current.results['EODMS RecordId'].tolist()
            order_ids = current.order(record_ids)
            LOGGER.info('EODMS Order Ids for tracking progress: %s' % order_ids)
        else:
            LOGGER.warn('No records to order')
