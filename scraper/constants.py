"""
Constants and static data for the scraper application.
Contains prefecture data, regions, and domain mappings.
"""

# French prefectures and their regions with government domains
PREFECTURES = [
    # Auvergne-Rhône-Alpes (12)
    {'name': 'Ain', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'ain.gouv.fr', 'code': '01'},
    {'name': 'Allier', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'allier.gouv.fr', 'code': '03'},
    {'name': 'Ardèche', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'ardeche.gouv.fr', 'code': '07'},
    {'name': 'Cantal', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'cantal.gouv.fr', 'code': '15'},
    {'name': 'Drôme', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'drome.gouv.fr', 'code': '26'},
    {'name': 'Isère', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'isere.gouv.fr', 'code': '38'},
    {'name': 'Loire', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'loire.gouv.fr', 'code': '42'},
    {'name': 'Haute-Loire', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'haute-loire.gouv.fr', 'code': '43'},
    {'name': 'Puy-de-Dôme', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'puy-de-dome.gouv.fr', 'code': '63'},
    {'name': 'Rhône', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'rhone.gouv.fr', 'code': '69'},
    {'name': 'Savoie', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'savoie.gouv.fr', 'code': '73'},
    {'name': 'Haute-Savoie', 'region': 'Auvergne-Rhône-Alpes', 'domain': 'haute-savoie.gouv.fr', 'code': '74'},

    # Bourgogne-Franche-Comté (8)
    {'name': "Côte-d'Or", 'region': 'Bourgogne-Franche-Comté', 'domain': 'cote-dor.gouv.fr', 'code': '21'},
    {'name': 'Doubs', 'region': 'Bourgogne-Franche-Comté', 'domain': 'doubs.gouv.fr', 'code': '25'},
    {'name': 'Jura', 'region': 'Bourgogne-Franche-Comté', 'domain': 'jura.gouv.fr', 'code': '39'},
    {'name': 'Nièvre', 'region': 'Bourgogne-Franche-Comté', 'domain': 'nievre.gouv.fr', 'code': '58'},
    {'name': 'Saône-et-Loire', 'region': 'Bourgogne-Franche-Comté', 'domain': 'saone-et-loire.gouv.fr', 'code': '71'},
    {'name': 'Yonne', 'region': 'Bourgogne-Franche-Comté', 'domain': 'yonne.gouv.fr', 'code': '89'},
    {'name': 'Haute-Saône', 'region': 'Bourgogne-Franche-Comté', 'domain': 'haute-saone.gouv.fr', 'code': '70'},
    {'name': 'Territoire-de-Belfort', 'region': 'Bourgogne-Franche-Comté', 'domain': 'territoire-de-belfort.gouv.fr', 'code': '90'},

    # Bretagne (4)
    {'name': "Côtes d'Armor", 'region': 'Bretagne', 'domain': 'cotes-darmor.gouv.fr', 'code': '22'},
    {'name': 'Finistère', 'region': 'Bretagne', 'domain': 'finistere.gouv.fr', 'code': '29'},
    {'name': 'Ille-et-Vilaine', 'region': 'Bretagne', 'domain': 'ille-et-vilaine.gouv.fr', 'code': '35'},
    {'name': 'Morbihan', 'region': 'Bretagne', 'domain': 'morbihan.gouv.fr', 'code': '56'},

    # Centre-Val de Loire (6)
    {'name': 'Cher', 'region': 'Centre-Val de Loire', 'domain': 'cher.gouv.fr', 'code': '18'},
    {'name': 'Eure-et-Loir', 'region': 'Centre-Val de Loire', 'domain': 'eure-et-loir.gouv.fr', 'code': '28'},
    {'name': 'Indre', 'region': 'Centre-Val de Loire', 'domain': 'indre.gouv.fr', 'code': '36'},
    {'name': 'Indre-et-Loire', 'region': 'Centre-Val de Loire', 'domain': 'indre-et-loire.gouv.fr', 'code': '37'},
    {'name': 'Loir-et-Cher', 'region': 'Centre-Val de Loire', 'domain': 'loir-et-cher.gouv.fr', 'code': '41'},
    {'name': 'Loiret', 'region': 'Centre-Val de Loire', 'domain': 'loiret.gouv.fr', 'code': '45'},

    # Grand Est (10)
    {'name': 'Ardennes', 'region': 'Grand Est', 'domain': 'ardennes.gouv.fr', 'code': '08'},
    {'name': 'Aube', 'region': 'Grand Est', 'domain': 'aube.gouv.fr', 'code': '10'},
    {'name': 'Marne', 'region': 'Grand Est', 'domain': 'marne.gouv.fr', 'code': '51'},
    {'name': 'Haute-Marne', 'region': 'Grand Est', 'domain': 'haute-marne.gouv.fr', 'code': '52'},
    {'name': 'Meurthe-et-Moselle', 'region': 'Grand Est', 'domain': 'meurthe-et-moselle.gouv.fr', 'code': '54'},
    {'name': 'Meuse', 'region': 'Grand Est', 'domain': 'meuse.gouv.fr', 'code': '55'},
    {'name': 'Moselle', 'region': 'Grand Est', 'domain': 'moselle.gouv.fr', 'code': '57'},
    {'name': 'Bas-Rhin', 'region': 'Grand Est', 'domain': 'bas-rhin.gouv.fr', 'code': '67'},
    {'name': 'Haut-Rhin', 'region': 'Grand Est', 'domain': 'haut-rhin.gouv.fr', 'code': '68'},
    {'name': 'Vosges', 'region': 'Grand Est', 'domain': 'vosges.gouv.fr', 'code': '88'},

    # Hauts-de-France (5)
    {'name': 'Aisne', 'region': 'Hauts-de-France', 'domain': 'aisne.gouv.fr', 'code': '02'},
    {'name': 'Nord', 'region': 'Hauts-de-France', 'domain': 'nord.gouv.fr', 'code': '59'},
    {'name': 'Oise', 'region': 'Hauts-de-France', 'domain': 'oise.gouv.fr', 'code': '60'},
    {'name': 'Pas-de-Calais', 'region': 'Hauts-de-France', 'domain': 'pas-de-calais.gouv.fr', 'code': '62'},
    {'name': 'Somme', 'region': 'Hauts-de-France', 'domain': 'somme.gouv.fr', 'code': '80'},

    # Île-de-France (8)
    {'name': 'Paris', 'region': 'Île-de-France', 'domain': 'paris.gouv.fr', 'code': '75'},
    {'name': 'Seine-et-Marne', 'region': 'Île-de-France', 'domain': 'seine-et-marne.gouv.fr', 'code': '77'},
    {'name': 'Yvelines', 'region': 'Île-de-France', 'domain': 'yvelines.gouv.fr', 'code': '78'},
    {'name': 'Essonne', 'region': 'Île-de-France', 'domain': 'essonne.gouv.fr', 'code': '91'},
    {'name': 'Hauts-de-Seine', 'region': 'Île-de-France', 'domain': 'hauts-de-seine.gouv.fr', 'code': '92'},
    {'name': 'Seine-Saint-Denis', 'region': 'Île-de-France', 'domain': 'seine-saint-denis.gouv.fr', 'code': '93'},
    {'name': 'Val-de-Marne', 'region': 'Île-de-France', 'domain': 'val-de-marne.gouv.fr', 'code': '94'},
    {'name': "Val-d'Oise", 'region': 'Île-de-France', 'domain': 'val-doise.gouv.fr', 'code': '95'},

    # Normandie (5)
    {'name': 'Calvados', 'region': 'Normandie', 'domain': 'calvados.gouv.fr', 'code': '14'},
    {'name': 'Eure', 'region': 'Normandie', 'domain': 'eure.gouv.fr', 'code': '27'},
    {'name': 'Manche', 'region': 'Normandie', 'domain': 'manche.gouv.fr', 'code': '50'},
    {'name': 'Orne', 'region': 'Normandie', 'domain': 'orne.gouv.fr', 'code': '61'},
    {'name': 'Seine-Maritime', 'region': 'Normandie', 'domain': 'seine-maritime.gouv.fr', 'code': '76'},

    # Nouvelle-Aquitaine (12)
    {'name': 'Charente', 'region': 'Nouvelle-Aquitaine', 'domain': 'charente.gouv.fr', 'code': '16'},
    {'name': 'Charente-Maritime', 'region': 'Nouvelle-Aquitaine', 'domain': 'charente-maritime.gouv.fr', 'code': '17'},
    {'name': 'Corrèze', 'region': 'Nouvelle-Aquitaine', 'domain': 'correze.gouv.fr', 'code': '19'},
    {'name': 'Creuse', 'region': 'Nouvelle-Aquitaine', 'domain': 'creuse.gouv.fr', 'code': '23'},
    {'name': 'Dordogne', 'region': 'Nouvelle-Aquitaine', 'domain': 'dordogne.gouv.fr', 'code': '24'},
    {'name': 'Gironde', 'region': 'Nouvelle-Aquitaine', 'domain': 'gironde.gouv.fr', 'code': '33'},
    {'name': 'Landes', 'region': 'Nouvelle-Aquitaine', 'domain': 'landes.gouv.fr', 'code': '40'},
    {'name': 'Lot-et-Garonne', 'region': 'Nouvelle-Aquitaine', 'domain': 'lot-et-garonne.gouv.fr', 'code': '47'},
    {'name': 'Pyrénées-Atlantiques', 'region': 'Nouvelle-Aquitaine', 'domain': 'pyrenees-atlantiques.gouv.fr', 'code': '64'},
    {'name': 'Deux-Sèvres', 'region': 'Nouvelle-Aquitaine', 'domain': 'deux-sevres.gouv.fr', 'code': '79'},
    {'name': 'Vienne', 'region': 'Nouvelle-Aquitaine', 'domain': 'vienne.gouv.fr', 'code': '86'},
    {'name': 'Haute-Vienne', 'region': 'Nouvelle-Aquitaine', 'domain': 'haute-vienne.gouv.fr', 'code': '87'},

    # Occitanie (13)
    {'name': 'Ariège', 'region': 'Occitanie', 'domain': 'ariege.gouv.fr', 'code': '09'},
    {'name': 'Aude', 'region': 'Occitanie', 'domain': 'aude.gouv.fr', 'code': '11'},
    {'name': 'Aveyron', 'region': 'Occitanie', 'domain': 'aveyron.gouv.fr', 'code': '12'},
    {'name': 'Gard', 'region': 'Occitanie', 'domain': 'gard.gouv.fr', 'code': '30'},
    {'name': 'Gers', 'region': 'Occitanie', 'domain': 'gers.gouv.fr', 'code': '32'},
    {'name': 'Haute-Garonne', 'region': 'Occitanie', 'domain': 'haute-garonne.gouv.fr', 'code': '31'},
    {'name': 'Hérault', 'region': 'Occitanie', 'domain': 'herault.gouv.fr', 'code': '34'},
    {'name': 'Lot', 'region': 'Occitanie', 'domain': 'lot.gouv.fr', 'code': '46'},
    {'name': 'Lozère', 'region': 'Occitanie', 'domain': 'lozere.gouv.fr', 'code': '48'},
    {'name': 'Hautes-Pyrénées', 'region': 'Occitanie', 'domain': 'hautes-pyrenees.gouv.fr', 'code': '65'},
    {'name': 'Pyrénées-Orientales', 'region': 'Occitanie', 'domain': 'pyrenees-orientales.gouv.fr', 'code': '66'},
    {'name': 'Tarn', 'region': 'Occitanie', 'domain': 'tarn.gouv.fr', 'code': '81'},
    {'name': 'Tarn-et-Garonne', 'region': 'Occitanie', 'domain': 'tarn-et-garonne.gouv.fr', 'code': '82'},

    # Pays de la Loire (5)
    {'name': 'Loire-Atlantique', 'region': 'Pays de la Loire', 'domain': 'loire-atlantique.gouv.fr', 'code': '44'},
    {'name': 'Maine-et-Loire', 'region': 'Pays de la Loire', 'domain': 'maine-et-loire.gouv.fr', 'code': '49'},
    {'name': 'Mayenne', 'region': 'Pays de la Loire', 'domain': 'mayenne.gouv.fr', 'code': '53'},
    {'name': 'Sarthe', 'region': 'Pays de la Loire', 'domain': 'sarthe.gouv.fr', 'code': '72'},
    {'name': 'Vendée', 'region': 'Pays de la Loire', 'domain': 'vendee.gouv.fr', 'code': '85'},

    # Provence-Alpes-Côte d'Azur (6)
    {'name': 'Alpes de Haute-Provence', 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'alpes-de-haute-provence.gouv.fr', 'code': '04'},
    {'name': 'Hautes-Alpes', 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'hautes-alpes.gouv.fr', 'code': '05'},
    {'name': 'Alpes-Maritimes', 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'alpes-maritimes.gouv.fr', 'code': '06'},
    {'name': "Bouches-du-Rhône", 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'bouches-du-rhone.gouv.fr', 'code': '13'},
    {'name': 'Var', 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'var.gouv.fr', 'code': '83'},
    {'name': 'Vaucluse', 'region': "Provence-Alpes-Côte d'Azur", 'domain': 'vaucluse.gouv.fr', 'code': '84'},

    # Corse (2)
    {'name': 'Corse-du-Sud', 'region': 'Corse', 'domain': 'corse-du-sud.gouv.fr', 'code': '2A'},
    {'name': 'Haute-Corse', 'region': 'Corse', 'domain': 'haute-corse.gouv.fr', 'code': '2B'}
]


# Helper functions for working with prefecture data
def get_prefectures_by_region(region_name):
    """
    Get all prefectures for a specific region.
    
    Args:
        region_name (str): Name of the region
        
    Returns:
        list: List of prefecture dictionaries for the region
    """
    return [p for p in PREFECTURES if p['region'] == region_name]

def get_prefecture_by_domain(domain):
    """
    Get prefecture data by domain name.
    
    Args:
        domain (str): Domain name (e.g., 'morbihan.gouv.fr')
        
    Returns:
        dict or None: Prefecture data if found, None otherwise
    """
    for prefecture in PREFECTURES:
        if prefecture['domain'] == domain:
            return prefecture
    return None

def get_all_regions():
    """
    Get list of all unique regions.
    
    Returns:
        list: List of unique region names
    """
    return list(set(p['region'] for p in PREFECTURES))

def get_all_domains():
    """
    Get list of all prefecture domains.
    
    Returns:
        list: List of all domain names
    """
    return [p['domain'] for p in PREFECTURES]
