import json

COMPETITIONS = [
    # Top Domestic Leagues
    "Premier League",         # England
    "LaLiga",                # Spain
    "Bundesliga",             # Germany
    "Serie A",                # Italy
    "Ligue 1",                # France
    "Eredivisie",             # Netherlands
    "Primeira Liga",          # Portugal
    "Belgian Pro League",     # Belgium
    "Scottish Premiership",   # Scotland
    "Super Lig",              # Turkey
    "Russian Premier League", # Russia
    "Greek Super League",     # Greece
    "Swiss Super League",     # Switzerland
    "Austrian Bundesliga",    # Austria
    "Danish Superliga",       # Denmark
    "Norwegian Eliteserien",  # Norway
    "Swedish Allsvenskan",    # Sweden

    # European Club Competitions
    "UEFA Champions League",             # Europe's premier club competition
    "UEFA Europa League",                # Second-tier competition
    "UEFA Europa Conference League",     # Third-tier competition
    "UEFA Super Cup",                    # Match between Champions League and Europa League winners
    "FIFA Club World Cup",               # Involves European champions among others

    # Domestic Cups (England)
    "FA Cup",                            # England's premier domestic cup
    "EFL Cup",             # English League Cup
    "Community Shield",                  # Pre-season match between league and FA Cup winners

    # Domestic Cups (Spain)
    "Copa del Rey",                      # Spain's premier domestic cup
    "Supercopa de España",               # Spanish Super Cup

    # Domestic Cups (Germany)
    "DFB-Pokal",                         # Germany's domestic cup
    "DFL-Supercup",                      # German Super Cup

    # Domestic Cups (Italy)
    "Coppa Italia",                      # Italy's domestic cup
    "Supercoppa Italiana",               # Italian Super Cup

    # Domestic Cups (France)
    "Coupe de France",                   # France's domestic cup
    "Trophée des Champions",             # French Super Cup

    # Domestic Cups (Netherlands)
    "KNVB Cup",                          # Dutch domestic cup
    "Johan Cruyff Shield",               # Dutch Super Cup

]

def match_competitions_with_ids(api_response_file):
    """Match competition names with their IDs, using country checks for top leagues"""
    with open(api_response_file, 'r') as f:
        api_data = json.load(f)
    
    # Define country mappings for top leagues only
    league_countries = {
        "Premier League": "england",
        "LaLiga": "spain",
        "Bundesliga": "germany",
        "Serie A": "italy",
        "Ligue 1": "france",
        "Eredivisie": "netherlands",
        "Primeira Liga": "portugal",
        "Belgian Pro League": "belgium",
        "Scottish Premiership": "scotland",
        "Super Lig": "turkey",
    }
    
    matched_competitions = {}
    unmatched_competitions = []
    
    # Create lookup dictionaries
    api_competitions = {}
    for comp in api_data['competitions']:
        name = comp['name'].lower()
        country = comp.get('category', {}).get('name', '').lower()
        
        # Store both with and without country context
        api_competitions[name] = {
            'id': comp['id'],
            'name': comp['name'],
            'country': country
        }
        api_competitions[f"{name}_{country}"] = {
            'id': comp['id'],
            'name': comp['name'],
            'country': country
        }
    
    for competition in COMPETITIONS:
        comp_lower = competition.lower()
        found = False
        
        # Check if it's a top league that needs country verification
        if competition in league_countries:
            expected_country = league_countries[competition]
            key = f"{comp_lower}_{expected_country}"
            if key in api_competitions:
                matched_competitions[competition] = api_competitions[key]
                found = True
        else:
            # For other competitions, try simple matching
            if comp_lower in api_competitions:
                matched_competitions[competition] = api_competitions[comp_lower]
                found = True
            else:
                # Try partial match
                for api_name, data in api_competitions.items():
                    if '_' not in api_name and (comp_lower in api_name or api_name in comp_lower):
                        matched_competitions[competition] = data
                        found = True
                        break
        
        if not found:
            unmatched_competitions.append(competition)
    
    # Print unmatched competitions
    if unmatched_competitions:
        print("\nUnmatched competitions:")
        for comp in unmatched_competitions:
            print(f"- {comp}")
    
    # Save results
    output_file = 'sportradar/data/top_competitions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matched_competitions, f, indent=4, ensure_ascii=False)
    
    print(f"\nMatched {len(matched_competitions)} competitions")
    print(f"Results saved to {output_file}")
    return matched_competitions

if __name__ == "__main__":
    match_competitions_with_ids('sportradar/data/competitions.json')