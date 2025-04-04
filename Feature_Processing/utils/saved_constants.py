COMPETITION_LIST_FOR_ODDS_API = ["soccer_epl","soccer_spain_la_liga","soccer_germany_bundesliga","soccer_italy_serie_a","soccer_france_ligue_one","soccer_uefa_champs_league","soccer_uefa_europa_league","soccer_uefa_europa_conference_league","soccer_fa_cup","soccer_england_efl_cup"]

# Competition tiers (1-6, 1 being highest)
COMPETITION_TIERS = {
    # Tier 1 - Elite European Competition
    'UEFA Champions League': 1,
    
    # Tier 2 - Top 5 Domestic Leagues
    'Premier League': 2,
    'LaLiga': 2,
    'Bundesliga': 2,
    'Serie A': 2,
    'Ligue 1': 2,
    
    # Tier 3 - Secondary European Competitions
    'UEFA Europa League': 3,
    'FIFA Club World Cup': 3,
    
    # Tier 4 - Major Domestic Cups & Strong Leagues
    'FA Cup': 4,
    'Copa del Rey': 4,
    'DFB-Pokal': 4,
    'Coppa Italia': 4,
    'Coupe de France': 4,
    'Eredivisie': 4,
    'UEFA Europa Conference League': 4,
    
    # Tier 5 - Secondary Domestic Cups & Other Leagues
    'EFL Cup': 5,
    'Swiss Super League': 5,
    'Austrian Bundesliga': 5,
    'Danish Superliga': 5,
    'Norwegian Eliteserien': 5,
    'Swedish Allsvenskan': 5,
    
    # Tier 6 - Super Cups
    'UEFA Super Cup': 6,
    'Community Shield': 6,
    'Supercopa': 6,
    'Supercoppa Italiana': 6
}

# Derby matches by competition
#TODO: Check team names are correct
DERBIES= {
    'Premier League': [
        ('Arsenal', 'Tottenham Hotspur'),  # North London Derby
        ('Liverpool', 'Everton'),  # Merseyside Derby
        ('Manchester United', 'Manchester City'),  # Manchester Derby
        ('Chelsea', 'Tottenham Hotspur'),  # London Derby
        ('Arsenal', 'Chelsea'),  # London Derby
    ],
    'LaLiga': [
        ('Real Madrid', 'Barcelona'),  # El Clásico
        ('Atletico Madrid', 'Real Madrid'),  # Madrid Derby
        ('Sevilla', 'Real Betis'),  # Seville Derby
        ('Athletic Bilbao', 'Real Sociedad'),  # Basque Derby
        ('Valencia', 'Villarreal'),  # Valencian Community Derby
    ],
    'Bundesliga': [
        ('Borussia Dortmund', 'Schalke 04'),  # Revierderby
        ('Bayern Munich', 'Borussia Dortmund'),  # Der Klassiker
        ('Hamburger SV', 'Werder Bremen'),  # Nordderby
        ('Bayern Munich', '1860 Munich'),  # Munich Derby (historical)
    ],
    'Serie A': [
        ('Inter Milano', 'AC Milan'),  # Derby della Madonnina
        ('AS Roma', 'Lazio Rome'),  # Derby della Capitale
        ('Juventus Turin', 'Torino FC'),  # Derby della Mole
        ('Napoli', 'Roma'),  # Derby del Sole
        ('Genoa', 'Sampdoria'),  # Derby della Lanterna
    ],
    'Ligue 1': [
        ('Paris Saint-Germain', 'Marseille'),  # Le Classique
        ('Lyon', 'Saint-Etienne'),  # Derby Rhône-Alpes
        ('Nice', 'Monaco'),  # Côte d'Azur Derby
    ],
    'Eredivisie': [
        ('Ajax', 'Feyenoord'),  # De Klassieker
        ('PSV Eindhoven', 'Ajax'),  # Dutch Derby
        ('Feyenoord', 'Sparta Rotterdam'),  # Rotterdam Derby
    ],
    'Swiss Super League': [
        ('FC Basel', 'FC Zürich'),  # Swiss Classic
        ('FC Zürich', 'Grasshopper Club Zürich'),  # Zurich Derby
        ('Young Boys', 'FC Basel'),  # Key Rivalry
    ],
    'Austrian Bundesliga': [
        ('Rapid Wien', 'Austria Wien'),  # Vienna Derby
        ('RB Salzburg', 'Rapid Wien'),  # Top Clash
    ],
    'Danish Superliga': [
        ('FC Copenhagen', 'Brøndby IF'),  # Copenhagen Derby
    ],
    'Norwegian Eliteserien': [
        ('Rosenborg', 'Molde'),  # Norwegian Classic
    ],
    'Swedish Allsvenskan': [
        ('AIK', 'Djurgården'),  # Stockholm Derby
        ('Malmö FF', 'Helsingborg'),  # Skåne Derby
    ],
    'UEFA Champions League': [],
    'UEFA Europa League': [],
    'UEFA Conference League': [],
    'UEFA Super Cup': [],
    'FIFA Club World Cup': [],
    'FA Cup': [],
    'EFL Cup': [],
    'Community Shield': [],
    'Copa del Rey': [],
    'Supercopa': [],
    'Coppa Italia': [],
    'Supercoppa Italiana': [],
    'Coupe de France': [],
}

