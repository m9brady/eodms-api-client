from datetime import datetime, timedelta
import click

from . import NAPL, Planet, RS1, RS2, RCM

@click.command(context_settings={
    'help_option_names': ['-h', '--help']
})
@click.option(
    '--username',
    '-u',
    help='EODMS username (leave blank to use .netrc or be prompted)'
)
@click.option(
    '--password',
    '-p',
    help='EODMS password (leave blank to use .netrc or be prompted)'
)
@click.option(
    '--collection',
    '-c',
    type=click.Choice(['RS1', 'RS2', 'RCM', 'NAPL', 'Planet']),
    help='EODMS collection to search'
)
@click.option(
    '--start',
    '-s',
    default=datetime.today() - timedelta(1),
    help='Beginning of acquisition time window (default to 1 day prior to now)'
)
@click.option(
    '--end',
    '-e',
    default=datetime.today(),
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
    '--rcm-satellite',
    '-r',
    type=click.Choice(['RCM1', 'RCM2', 'RCM3']),
    help='Limit results to the desired RCM satellite'
)
@click.option(
    '--product-type',
    '-p',
    default=None,
    help='Limit results to a certain image product type'
)
@click.option(
    '--dump-query',
    is_flag=True,
    default=True,
    help='Whether or not to create a geopackage containing the results of the query (default True)'
)
@click.option(
    '--submit-order',
    is_flag=True,
    default=False,
    help='Submit an order to EODMS from the results of the current query parameters (default False)'
)
@click.option(
    
)
def cli(
    username,
    password,

):
    params = {
        
    }