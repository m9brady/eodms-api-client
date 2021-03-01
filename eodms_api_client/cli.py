import logging
import os

import click

from . import EodmsAPI
from . import __version__ as eodms_version

LOGGER = logging.getLogger('eodmsapi.cli')
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', '%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

def print_version(ctx, param, value):
    '''stolen from Click documentation: https://click.palletsprojects.com/en/7.x/options/#callbacks-and-eager-options'''
    if not value or ctx.resilient_parsing:
        return
    click.echo(f'eodms-api-client {eodms_version}')
    ctx.exit()

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
    type=str,
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
    '--incidence-angle-low',
    '-ial',
    default=None,
    help='Limit results to scenes that have incidence angles greater than this value (degrees)'
)
@click.option(
    '--incidence-angle-high',
    '-iah',
    default=None,
    help='Limit results to scenes that have incidence angles less than this value (degrees)'
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
    '--cloud-cover',
    '-cc',
    default=None,
    help='Limit optical results to have less than this amount of cloud cover [0-100]'
)
@click.option(
    '--output-dir',
    '-o',
    type=click.Path(exists=True),
    default='.',
    help='Directory where query results and downloaded imagery will be saved',
    show_default=True
)
@click.option(
    '--dump-results',
    '-dr',
    is_flag=True,
    default=False,
    help='Whether or not to create a geojson dump containing the results of the query'
)
@click.option(
    '--dump-filename',
    '-dfn',
    type=str,
    default='query_results',
    help='Filename for query results geojson',
    show_default=True
)
@click.option(
    '--submit-order',
    is_flag=True,
    default=False,
    help='Submit an order to EODMS from the results of the current query parameters'
)
@click.option(
    '--record-id',
    default=None,
    help='Specific record Id to order from the desired collection'
)
@click.option(
    '--record-ids',
    type=click.Path(exists=True),
    default=None,
    help='File of line-separated record Ids to order from the desired collection'
)
@click.option(
    '--download-id',
    default=None,
    help='Specific Order item Id to download from EODMS'
)
@click.option(
    '--download-ids',
    type=click.Path(exists=True),
    default=None,
    help='File of line-separated Order item Ids to download from EODMS'
)
@click.option(
    '--log-verbose',
    is_flag=True,
    default=False,
    help='Use debug-level logging'
)
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help='Show the package version'
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
    incidence_angle_low,
    incidence_angle_high,
    radarsat_beam_mode,
    radarsat_beam_mnemonic,
    radarsat_polarization,
    radarsat_orbit_direction,
    radarsat_look_direction,
    radarsat_downlink_segment_id,
    rcm_satellite,
    cloud_cover,
    output_dir,
    dump_results,
    dump_filename,
    submit_order,
    record_id,
    record_ids,
    download_id,
    download_ids,
    log_verbose
):
    if log_verbose:
        LOGGER.setLevel(logging.DEBUG)
    LOGGER.debug('Connecting to EODMS')
    current = EodmsAPI(collection=collection, username=username, password=password)
    LOGGER.debug('Connected to EODMS')
    # check for presence of supplied record_ids, where we just skip ahead and order
    if record_id is not None:
        LOGGER.info('Fast-ordering for single record')
        order_ids = current.order(record_id)
        LOGGER.info('EODMS Order Ids for tracking progress: %s' % order_ids)
        exit()
    elif record_ids is not None:
        with open(record_ids) as f:
            records_to_order = [int(line.strip()) for line in f.readlines() if line.strip() != '']
        LOGGER.info('Fast-ordering for %d record(s)' % len(records_to_order))
        order_ids = current.order(records_to_order)
        LOGGER.info('EODMS Order Ids for tracking progress: %s' % order_ids)
    # check for presence of supplied item_ids, where we just skip ahead and try to download
    elif download_id is not None:
        LOGGER.info('Fast-downloading for 1 order')
        current.download(download_id, output_dir)
    elif download_ids is not None:
        with open(download_ids) as f:
            item_ids = [line for line in f.read().splitlines() if line != '']
        if len(item_ids) == 0:
            raise IOError('No item_ids detected in file: %s' % download_ids)
        LOGGER.info('Fast-downloading for %d order(s)' % len(item_ids))
        current.download(item_ids, output_dir)
    else:
        # otherwise, run a query
        LOGGER.info('Querying EODMS API')
        current.query(
            start=start, end=end, geometry=geometry, product_type=product_type,
            product_format=product_format, absolute_orbit=absolute_orbit,
            relative_orbit=relative_orbit, incidence_angle=incidence_angle,
            incidence_angle_low=incidence_angle_low, incidence_angle_high=incidence_angle_high,
            beam_mode=radarsat_beam_mode, mnemonic=radarsat_beam_mnemonic, 
            polarization=radarsat_polarization, downlink_segment=radarsat_downlink_segment_id,
            orbit_direction=radarsat_orbit_direction,
            look_direction=radarsat_look_direction, rcm_satellite=rcm_satellite,
            cloud_cover=cloud_cover
        )
        n_results = len(current.results)
        LOGGER.info('Finished query. %d result%s' % (
            n_results,
            's' if n_results != 1 else ''
        ))
    if dump_results:
        out_file = os.path.join(output_dir, f'{dump_filename}.geojson')
        LOGGER.info('Saving query result%s to file: %s' % (
            's' if n_results != 1 else '',
            out_file
        ))
        if len(current.results) > 0:
            current.results.to_file(out_file, driver='GeoJSON')
        else:
            LOGGER.warn('No results found')
    if submit_order:
        if len(current.results) > 0:
            LOGGER.info('Submitting order for %d records' % len(current.results))
            to_order = current.results['EODMS RecordId'].tolist()
            item_ids = current.order(to_order)
            LOGGER.info('EODMS Item Ids for tracking status and downloading: %s' % item_ids)
        else:
            LOGGER.warn('No records to order')
