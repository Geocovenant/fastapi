"""Insert initial data from JSON files

Revision ID: insert_initial_data
Revises: 4f99c767e8c0
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json
from pathlib import Path

# revision identifiers, used by Alembic.
revision = 'insert_initial_data'
down_revision = '4f99c767e8c0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Crear conexión
    conn = op.get_bind()
    
    # Obtener las tablas
    country_table = sa.Table(
        'country',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('area', sa.Float()),
        sa.Column('borders', sa.String()),
        sa.Column('capital_latlng', sa.String()),
        sa.Column('capital', sa.String()),
        sa.Column('cca2', sa.String()),
        sa.Column('cca3', sa.String()),
        sa.Column('coat_of_arms_svg', sa.String()),
        sa.Column('currency_code', sa.String()),
        sa.Column('currency_name', sa.String()),
        sa.Column('flag', sa.String()),
        sa.Column('google_maps_link', sa.String()),
        sa.Column('idd_root', sa.String()),
        sa.Column('idd_suffixes', sa.String()),
        sa.Column('landlocked', sa.Boolean()),
        sa.Column('languages', sa.String()),
        sa.Column('native_name', sa.String()),
        sa.Column('numeric_code', sa.String()),
        sa.Column('openstreetmap_link', sa.String()),
        sa.Column('population', sa.Integer()),
        sa.Column('region', sa.String()),
        sa.Column('status', sa.String()),
        sa.Column('subregion', sa.String()),
        sa.Column('timezone', sa.String()),
    )

    subnation_table = sa.Table(
        'subnation',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('country_id', sa.Integer()),
        sa.Column('area', sa.Float()),
        sa.Column('population', sa.Integer()),
        sa.Column('borders', sa.String()),
        sa.Column('capital', sa.String()),
        sa.Column('flag', sa.String()),
        sa.Column('iso_code', sa.String()),
        sa.Column('timezone', sa.String()),
        sa.Column('famous_landmark', sa.String()),
    )

    community_table = sa.Table(
        'community',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('description', sa.String()),
        sa.Column('level', sa.String()),
        sa.Column('parent_id', sa.Integer()),
    )

    # Limpiar datos existentes
    op.execute("TRUNCATE TABLE community CASCADE")
    op.execute("TRUNCATE TABLE subnation CASCADE")
    op.execute("TRUNCATE TABLE country CASCADE")
    
    # Reiniciar las secuencias
    op.execute("ALTER SEQUENCE country_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE subnation_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE community_id_seq RESTART WITH 1")

    # Cargar datos de los archivos JSON
    base_path = Path(__file__).parent.parent.parent

    # Primero crear la comunidad global
    global_community = {
        'name': 'Global',
        'description': 'Global Community',
        'parent_id': None,
        'level': 'GLOBAL',
    }
    op.bulk_insert(community_table, [global_community])
    
    # Crear comunidades para los continentes
    continents = [
        {'name': 'Africa', 'region': 'Africa'},
        {'name': 'Americas', 'region': 'Americas'},
        {'name': 'Asia', 'region': 'Asia'},
        {'name': 'Europe', 'region': 'Europe'},
        {'name': 'Oceania', 'region': 'Oceania'},
    ]
    
    continent_communities = []
    for continent in continents:
        continent_community = {
            'name': continent['name'],
            'description': f'{continent["name"]} Continental Community',
            'parent_id': 1,  # Global community ID
            'level': 'CONTINENT',
        }
        continent_communities.append(continent_community)
    
    op.bulk_insert(community_table, continent_communities)
    
    # Insertar países y sus comunidades
    with open(base_path / 'api' / 'data' / 'countries.json', 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
        formatted_countries = []
        country_communities = []
        
        for country in countries_data:
            # Formatear país para la tabla country
            currencies = country.get('currencies', {})
            currency_code = next(iter(currencies.keys())) if currencies else None
            currency_name = currencies[currency_code]['name'] if currency_code else None if currencies else None
            
            idd = country.get('idd', {})
            languages = country.get('languages', {})
            native_names = country.get('name', {}).get('nativeName', {})
            native_name = next(iter(native_names.values()))['common'] if native_names else None

            formatted_country = {
                'name': country.get('name', {}).get('common', ''),
                'area': country.get('area'),
                'borders': ','.join(country.get('borders', [])),
                'capital_latlng': ','.join(map(str, country.get('capitalInfo', {}).get('latlng', []))),
                'capital': country.get('capital', [''])[0] if country.get('capital') else None,
                'cca2': country.get('cca2'),
                'cca3': country.get('cca3'),
                'coat_of_arms_svg': country.get('coatOfArms', {}).get('svg'),
                'currency_code': currency_code,
                'currency_name': currency_name,
                'flag': country.get('flag'),
                'google_maps_link': country.get('maps', {}).get('googleMaps'),
                'idd_root': idd.get('root'),
                'idd_suffixes': ','.join(idd.get('suffixes', [])),
                'landlocked': country.get('landlocked'),
                'languages': ','.join(languages.values()) if languages else None,
                'native_name': native_name,
                'numeric_code': country.get('ccn3'),
                'openstreetmap_link': country.get('maps', {}).get('openStreetMaps'),
                'population': country.get('population'),
                'region': country.get('region'),
                'status': country.get('status'),
                'subregion': country.get('subregion'),
                'timezone': country.get('timezones', [''])[0] if country.get('timezones') else None,
            }
            formatted_countries.append(formatted_country)

            # Crear comunidad para el país
            region = country.get('region', '')
            parent_id = None
            if region == 'Africa': parent_id = 2
            elif region == 'Americas': parent_id = 3
            elif region == 'Asia': parent_id = 4
            elif region == 'Europe': parent_id = 5
            elif region == 'Oceania': parent_id = 6

            country_community = {
                'name': country.get('name', {}).get('common', ''),
                'description': f"National community of {country.get('name', {}).get('common', '')}",
                'parent_id': parent_id,
                'level': 'NATIONAL',
            }
            country_communities.append(country_community)

        op.bulk_insert(country_table, formatted_countries)
        op.bulk_insert(community_table, country_communities)

    # Insertar subnaciones y sus comunidades
    with open(base_path / 'api' / 'data' / 'subnations.json', 'r', encoding='utf-8') as f:
        subnations_data = json.load(f)
        formatted_subnations = []
        subnation_communities = []
        
        for subnation in subnations_data:
            # Formatear subnación para la tabla subnation
            formatted_subnation = {
                'name': subnation.get('name', ''),
                'country_id': subnation.get('country_id', None),
                'area': subnation.get('area', 0.0),
                'population': subnation.get('population', 0),
                'borders': ','.join(subnation.get('borders', [])),
                'capital': subnation.get('capital', ''),
                'flag': subnation.get('flag', ''),
                'iso_code': subnation.get('iso_code', ''),
                'timezone': subnation.get('timezone', ''),
                'famous_landmark': subnation.get('famous_landmark', ''),
            }
            formatted_subnations.append(formatted_subnation)

            # Crear comunidad para la subnación
            country_id = subnation.get('country_id')
            parent_id = country_id + 6 if country_id is not None else None
            
            subnation_community = {
                'name': subnation.get('name', ''),
                'description': f"Subnational community of {subnation.get('name', '')}",
                'parent_id': parent_id,
                'level': 'SUBNATIONAL',
            }
            subnation_communities.append(subnation_community)

        op.bulk_insert(subnation_table, formatted_subnations)
        op.bulk_insert(community_table, subnation_communities)

def downgrade() -> None:
    # Limpiar las tablas en caso de downgrade
    op.execute("TRUNCATE TABLE community CASCADE")
    op.execute("TRUNCATE TABLE subnation CASCADE")
    op.execute("TRUNCATE TABLE country CASCADE")