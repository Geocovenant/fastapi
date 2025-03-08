"""Insert initial data from JSON files

Revision ID: insert_initial_data
Revises: 0581ec5aec3a
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json
from pathlib import Path

# revision identifiers, used by Alembic.
revision = 'insert_initial_data'
down_revision = '0581ec5aec3a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Crear conexión
    conn = op.get_bind()
    base_path = Path(__file__).resolve().parent.parent.parent
    
    # Obtener las tablas
    country_table = sa.Table(
        'country',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('community_id', sa.Integer()),
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
        sa.Column('administrative_division_type', sa.String()),
    )

    region_table = sa.Table(
        'region',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('country_id', sa.Integer()),
        sa.Column('country_cca2', sa.String()),
        sa.Column('area', sa.Float()),
        sa.Column('population', sa.Integer()),
        sa.Column('borders', sa.String()),
        sa.Column('capital', sa.String()),
        sa.Column('flag', sa.String()),
        sa.Column('iso_code', sa.String()),
        sa.Column('timezone', sa.String()),
        sa.Column('famous_landmark', sa.String()),
        sa.Column('community_id', sa.Integer()),
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

    continent_table = sa.Table(
        'continent',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('community_id', sa.Integer()),
    )

    # Limpiar datos existentes
    op.execute("TRUNCATE TABLE community CASCADE")
    op.execute("TRUNCATE TABLE region CASCADE")
    op.execute("TRUNCATE TABLE country CASCADE")
    
    # Reiniciar las secuencias
    op.execute("ALTER SEQUENCE country_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE region_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE community_id_seq RESTART WITH 1")

    # 1. Primero insertar la comunidad global
    global_community = {
        'id': 1,
        'name': 'Global',
        'description': 'Global Community',
        'level': 'GLOBAL',
        'parent_id': None
    }
    op.bulk_insert(community_table, [global_community])

    # 2. Luego insertar las comunidades de los continentes
    with open(base_path / 'api' / 'data' / 'continents.json', 'r', encoding='utf-8') as f:
        continents_data = json.load(f)
        continent_communities = []
        formatted_continents = []
        
        for i, continent in enumerate(continents_data):
            community = {
                'id': i + 2,  # IDs 2-7
                'name': continent['name'],
                'description': f"Continental community of {continent['name']}",
                'parent_id': 1,  # ID de la comunidad global
                'level': 'CONTINENT'
            }
            continent_communities.append(community)

            # Formatear los datos del continente incluyendo el community_id
            formatted_continent = {
                'id': i + 1,
                'name': continent['name'],
                'community_id': i + 2  # Mismo ID que su comunidad
            }
            formatted_continents.append(formatted_continent)

        # Primero insertamos las comunidades
        op.bulk_insert(community_table, continent_communities)
        # Luego insertamos los continentes con sus community_ids
        op.bulk_insert(continent_table, formatted_continents)

    # 3. Luego insertar las comunidades de los países
    with open(base_path / 'api' / 'data' / 'countries.json', 'r', encoding='utf-8') as f:
        countries_data = json.load(f)
        country_communities = []
        country_communities_map = {}  # Para mapear cca2 -> community
        
        for i, country in enumerate(countries_data):
            if country.get('name', {}).get('common') == 'Antarctica':
                continue
            
            region = country.get('region', '')
            parent_id = None
            if region == 'Africa': parent_id = 2
            elif region == 'Americas': parent_id = 3
            elif region == 'Asia': parent_id = 4
            elif region == 'Europe': parent_id = 5
            elif region == 'Oceania': parent_id = 6

            community = {
                'id': i + 8,  # IDs empiezan en 8
                'name': country.get('name', {}).get('common', ''),
                'description': f"National community of {country.get('name', {}).get('common', '')}",
                'parent_id': parent_id,
                'level': 'NATIONAL'
            }
            country_communities.append(community)
            country_communities_map[country.get('cca2')] = community

        op.bulk_insert(community_table, country_communities)

        # Insertar los países
        formatted_countries = []
        for i, country in enumerate(countries_data):
            if country.get('name', {}).get('common') == 'Antarctica':
                continue
                
            formatted_country = {
                'name': country.get('name', {}).get('common', ''),
                'community_id': i + 8,  # Mismo ID que su comunidad
                'area': country.get('area'),
                'borders': ','.join(country.get('borders', [])),
                'capital_latlng': ','.join(map(str, country.get('capitalInfo', {}).get('latlng', []))),
                'capital': country.get('capital', [''])[0] if country.get('capital') else None,
                'cca2': country.get('cca2'),
                'cca3': country.get('cca3'),
                'coat_of_arms_svg': country.get('coatOfArms', {}).get('svg'),
                'currency_code': next(iter(country.get('currencies', {}).keys())) if country.get('currencies') else None,
                'currency_name': next(iter(country.get('currencies', {}).values())).get('name') if country.get('currencies') else None,
                'flag': country.get('flag'),
                'google_maps_link': country.get('maps', {}).get('googleMaps'),
                'idd_root': country.get('idd', {}).get('root'),
                'idd_suffixes': ','.join(country.get('idd', {}).get('suffixes', [])) if country.get('idd') else None,
                'landlocked': country.get('landlocked'),
                'languages': ','.join(country.get('languages', {}).values()) if country.get('languages') else None,
                'native_name': (
                    next(iter(country.get('name', {})
                        .get('nativeName', {})
                        .values()))
                        .get('common') 
                    if country.get('name', {}).get('nativeName') 
                    else None
                ),
                'numeric_code': country.get('ccn3'),
                'openstreetmap_link': country.get('maps', {}).get('openStreetMaps'),
                'population': country.get('population'),
                'region': country.get('region'),
                'status': country.get('status'),
                'subregion': country.get('subregion'),
                'timezone': country.get('timezones', [''])[0] if country.get('timezones') else None,
                'administrative_division_type': country.get('administrative_division_type'),
            }
            formatted_countries.append(formatted_country)

        op.bulk_insert(country_table, formatted_countries)

    # 4. Insertar regiones y sus comunidades
    with open(base_path / 'api' / 'data' / 'regions.json', 'r', encoding='utf-8') as f:
        regions_data = json.load(f)
        region_communities = []
        formatted_regions = []
        
        # Obtener el último ID de comunidad usado
        result = conn.execute(sa.text("SELECT MAX(id) FROM community"))
        next_community_id = (result.scalar() or 0) + 1
        
        for region in regions_data:
            # Obtener el ID del país usando el código cca2
            country_result = conn.execute(
                sa.text("SELECT id FROM country WHERE cca2 = :code"),
                {"code": region['country']}
            ).fetchone()
            
            if not country_result:
                print(f"País no encontrado para código: {region['country']}")
                continue
            
            country_id = country_result[0]
            
            # Crear comunidad para la región
            region_community = {
                'id': next_community_id,
                'name': region['name'],
                'description': f"Regional community of {region['name']}",
                'level': 'REGIONAL',
                'parent_id': country_communities_map[region['country']]['id']
            }
            region_communities.append(region_community)
            
            # Formatear región con el country_id
            formatted_region = {
                'name': region['name'],
                'country_id': country_id,  # Aquí asignamos el country_id
                'country_cca2': region['country'],
                'area': float(region.get('area', 0.0)),
                'population': int(region.get('population', 0)),
                'borders': ','.join(region.get('borders', [])),
                'capital': region.get('capital', ''),
                'flag': region.get('flag', ''),
                'iso_code': region.get('additional_info', {}).get('iso_code', ''),
                'timezone': region.get('additional_info', {}).get('timezone', ''),
                'famous_landmark': region.get('additional_info', {}).get('famous_landmark', ''),
                'community_id': next_community_id
            }
            formatted_regions.append(formatted_region)
            next_community_id += 1
        
        # Insertar comunidades de regiones
        if region_communities:
            op.bulk_insert(community_table, region_communities)
        
        # Insertar regiones
        if formatted_regions:
            op.bulk_insert(region_table, formatted_regions)

    # Crear tabla para subregion
    subregion_table = sa.Table(
        'subregion',
        sa.MetaData(),
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String()),
        sa.Column('area', sa.Float()),
        sa.Column('population', sa.Integer()),
        sa.Column('borders', sa.String()),
        sa.Column('capital', sa.String()),
        sa.Column('website', sa.String()),
        sa.Column('head_of_government', sa.String()),
        sa.Column('head_of_government_title', sa.String()),
        sa.Column('community_id', sa.Integer()),
        sa.Column('region_id', sa.Integer()),
    )

    # 5. Insertar subregions y sus comunidades
    with open(base_path / 'api' / 'data' / 'subregions.json', 'r', encoding='utf-8') as f:
        subregions_data = json.load(f)
        
        # Obtener el último ID de comunidad usado
        result = conn.execute(sa.text("SELECT MAX(id) FROM community"))
        last_community_id = result.scalar() or 0
        next_community_id = last_community_id + 1

        # Para almacenar todas las inserciones
        division_communities = []
        formatted_divisions = []

        # Iterar sobre cada país en el JSON
        for country_data in subregions_data:
            for country_code, provinces in country_data.items():
                # Obtener el ID del país
                country_result = conn.execute(
                    sa.text("SELECT id FROM country WHERE cca2 = :code"),
                    {"code": country_code}
                ).fetchone()
                
                if not country_result:
                    print(f"País no encontrado: {country_code}")
                    continue

                country_id = country_result[0]

                # Iterar sobre cada provincia y sus divisiones
                for province_slug, divisions in provinces.items():
                    # Convertir el slug a un nombre más amigable
                    province_name = province_slug.replace('-', ' ').title()
                    
                    print(f"Buscando subnación para: {province_slug} en país {country_code}")
                    # Obtener todas las subnaciones del país para debug
                    regions = conn.execute(
                        sa.text("SELECT id, name FROM region WHERE country_cca2 = :country_cca2"),
                        {"country_cca2": country_code}
                    ).fetchall()
                    print(f"Subnaciones disponibles para {country_code}:", [s[1] for s in regions])
                    
                    # Obtener el ID de la subnación
                    region_result = conn.execute(
                        sa.text("""
                            SELECT s.id 
                            FROM region s
                            JOIN country c ON s.country_cca2 = c.cca2
                            WHERE c.cca2 = :country_code 
                            AND LOWER(s.name) = :name
                        """),
                        {
                            "country_code": country_code,
                            "name": province_name.lower()
                        }
                    ).fetchone()

                    if not region_result:
                        print(f"Subnación no encontrada: {province_name} ({country_code})")
                        continue

                    region_id = region_result[0]
                    print(f"Subnación encontrada con ID: {region_id}")

                    # Procesar cada división
                    for division in divisions:
                        # Crear comunidad para la división
                        community = {
                            'id': next_community_id,
                            'name': division['name'],
                            'description': f"Subregional community of {division['name']}",
                            'parent_id': region_id + 7,  # ID de la comunidad de la subnación
                            'level': 'SUBREGIONAL'  # Cambiado de 'LOCAL' a 'SUBREGIONAL'
                        }
                        division_communities.append(community)

                        # Formatear división
                        formatted_division = {
                            'name': division['name'],
                            'area': float(division.get('area', 0.0)),
                            'population': int(division.get('population', 0)),
                            'borders': ','.join(division.get('borders', [])),
                            'capital': division.get('capital', ''),
                            'website': division.get('website', ''),
                            'head_of_government': division.get('head_of_government', ''),
                            'head_of_government_title': division.get('head_of_government_title', ''),
                            'community_id': next_community_id,
                            'region_id': region_id
                        }
                        formatted_divisions.append(formatted_division)
                        next_community_id += 1

        # Insertar las comunidades y divisiones
        if division_communities:
            print(f"Insertando {len(division_communities)} comunidades")
            op.bulk_insert(community_table, division_communities)
        if formatted_divisions:
            print(f"Insertando {len(formatted_divisions)} divisiones")
            op.bulk_insert(subregion_table, formatted_divisions)

def downgrade() -> None:
    # Limpiar las tablas en caso de downgrade
    op.execute("TRUNCATE TABLE community CASCADE")
    op.execute("TRUNCATE TABLE region CASCADE")
    op.execute("TRUNCATE TABLE country CASCADE")