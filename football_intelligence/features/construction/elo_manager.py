import math

from football_intelligence.features.construction.continent_mapping import (
    COUNTRY_TO_CONTINENT,
)
from football_intelligence.features.construction.elo_helpers import (
    build_elo_history_record,
    calculate_elo_ratings,
    get_bulk_entity_elos,
    get_counts,
    save_elo_future_bulk,
    save_elo_history_bulk,
    save_updated_counts,
    save_updated_elos_bulk,
)
from football_intelligence.features.construction.match_inputs import (
    extract_competition_ids,
    extract_league_ids,
    extract_nation_names,
    extract_team_id_name_map,
    extract_team_ids,
)


class EloManager:
    def __init__(self, conn, matches, mode='training'):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'

    def __enter__(self):
        self.team_id_name_map = extract_team_id_name_map(self.matches)
        self.team_ids = extract_team_ids(self.matches)
        self.nation_names = extract_nation_names(self.matches)
        print(self.nation_names)
        self.league_ids = extract_league_ids(self.matches)
        self.competition_ids = extract_competition_ids(self.matches)

        self.continent_names = [COUNTRY_TO_CONTINENT.get(nation, 'World') for nation in self.nation_names]

        self.club_elos = get_bulk_entity_elos(self.conn, 'club_elo_ratings', 'team_id', self.team_ids, self.team_id_name_map)
        self.nation_elos = get_bulk_entity_elos(self.conn, 'nation_elo_ratings', 'nation_name', self.nation_names)
        self.league_elos = get_bulk_entity_elos(self.conn, 'league_elo_ratings', 'league_id', self.league_ids)
        self.continent_elos = get_bulk_entity_elos(self.conn, 'continent_elo_ratings', 'continent_name', self.continent_names)

        self.counts = get_counts(self.conn, self.competition_ids, get_nation=False)

        self.elo_history = []
        return self

    def process_match(self, match):
        match_id = match['match_id']
        start_time = match['start_time']
        home_team_id = match['home_team_id']
        away_team_id = match['away_team_id']
        home_team_name = match.get('home_team_name', f"Team {home_team_id}")
        away_team_name = match.get('away_team_name', f"Team {away_team_id}")
        competition_id = match.get('competition_id')
        if competition_id is None:
            raise ValueError(f"Match {match_id} has no competition_id.")
        home_team_domestic_country = match['home_team_domestic_country']
        away_team_domestic_country = match['away_team_domestic_country']
        home_team_domestic_league_id = match['home_team_domestic_league_id']
        away_team_domestic_league_id = match['away_team_domestic_league_id']

        if match_id == 1321688:
            print(home_team_domestic_league_id, away_team_domestic_league_id)

        #map domestic country to continent
        home_team_continent = COUNTRY_TO_CONTINENT.get(home_team_domestic_country, 'World')
        away_team_continent = COUNTRY_TO_CONTINENT.get(away_team_domestic_country, 'World')

        # For inference mode, we don't have scores
        if self.mode == 'inference':
            home_score = None
            away_score = None
        else:
            home_score = match['home_score']
            away_score = match['away_score']

        # Check match type flags
        if match_id == 1321688:
            print(home_team_domestic_country, away_team_domestic_country, home_team_domestic_league_id, away_team_domestic_league_id)
        is_same_nation = home_team_domestic_country == away_team_domestic_country
        is_same_league = home_team_domestic_league_id == away_team_domestic_league_id
        is_domestic = is_same_nation and not is_same_league
        is_international = not is_same_nation
        is_same_continent = home_team_continent == away_team_continent

        # Get current elos from in-memory dictionaries
        home_club_elos = self.club_elos.get(home_team_id, {})
        away_club_elos = self.club_elos.get(away_team_id, {})
        home_nation_elos = self.nation_elos.get(home_team_domestic_country, {})
        away_nation_elos = self.nation_elos.get(away_team_domestic_country, {})
        home_league_elos = self.league_elos.get(home_team_domestic_league_id, {})
        away_league_elos = self.league_elos.get(away_team_domestic_league_id, {})
        home_continent_elos = self.continent_elos.get(home_team_continent, {})
        away_continent_elos = self.continent_elos.get(away_team_continent, {})

        # Calculate league probabilities
        league_counts = self.counts.get(str(competition_id), {'home_wins': 0, 'draw_wins': 0, 'away_wins': 0, 'count': 0})

        home_wins = league_counts.get('home_wins', 0)
        draw_wins = league_counts.get('draw_wins', 0)
        away_wins = league_counts.get('away_wins', 0)
        total_results = home_wins + draw_wins + away_wins

        # Calculate probabilities
        if total_results == 0:
            probability_home_win = 0.4
            probability_draw = 0.2
            probability_away_win = 0.4
        else:
            probability_home_win = home_wins / total_results
            probability_draw = draw_wins / total_results
            probability_away_win = away_wins / total_results

        # Calculate k_draw and eta parameters
        denominator = math.sqrt(probability_home_win * probability_away_win)
        if denominator == 0:
            k_draw_parameter = 0.25
            eta_home_advantage = 0.3
        else:
            k_draw_parameter = probability_draw / denominator
            eta_home_advantage = math.log10(probability_home_win / probability_away_win)

        # Save current elo history
        record = build_elo_history_record(
            match_id, start_time, home_team_id, away_team_id, home_team_name, away_team_name,
            home_club_elos, away_club_elos, 
            home_nation_elos, away_nation_elos,
            home_league_elos, away_league_elos,
            home_continent_elos, away_continent_elos,
            home_score, away_score,
            k_draw_parameter, eta_home_advantage)
        
        self.elo_history.append(record)

        # STOP HERE FOR INFERENCE MODE - Don't update ELOs or counts
        if self.mode == 'inference':
            return

        # TRAINING MODE ONLY: Update ELOs and counts based on match results
        # Define k values for ELO calculations
        k_values = [5, 10, 20, 30, 40, 80]

        # Create copies for updates
        updated_home_club = home_club_elos.copy()
        updated_away_club = away_club_elos.copy()
        updated_home_nation = home_nation_elos.copy()
        updated_away_nation = away_nation_elos.copy()
        updated_home_league = home_league_elos.copy()
        updated_away_league = away_league_elos.copy()
        updated_home_continent = home_continent_elos.copy()
        updated_away_continent = away_continent_elos.copy()

        # Update Continent ELOs
        if not is_same_continent:
            updated_home_continent, updated_away_continent = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_continent, updated_away_continent,
                'continent_elo_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update Nation ELOs
        if not is_same_nation:
            updated_home_nation, updated_away_nation = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_nation, updated_away_nation,
                'nation_elo_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update League ELOs
        if is_domestic:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_league, updated_away_league,
                'league_domestic_elo_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update Continental ELOs
        if not is_same_league and not is_same_nation:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_league, updated_away_league,
                'league_continental_elo_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )
        
        # Update Intercontinental ELOs
        if not is_same_continent:
            updated_home_league, updated_away_league = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_league, updated_away_league,
                'league_intercontinental_elo_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update Club ELOs - General
        updated_home_club, updated_away_club = calculate_elo_ratings(
            self.conn, home_score, away_score,
            updated_home_club, updated_away_club,
            'elo_k', k_values, f"{home_team_name} vs {away_team_name}",
            k_draw_parameter, eta_home_advantage
        )

        # Update Home-specific ELOs
        home_temp = updated_home_club.copy()
        updated_home_club, _ = calculate_elo_ratings(
            self.conn, home_score, away_score,
            updated_home_club, home_temp,
            'elo_home_matches_k', k_values, f"{home_team_name} vs {away_team_name}",
            k_draw_parameter, eta_home_advantage
        )

        # Update Away-specific ELOs
        away_temp = updated_away_club.copy()
        _, updated_away_club = calculate_elo_ratings(
            self.conn, home_score, away_score,
            away_temp, updated_away_club,
            'elo_away_matches_k', k_values, f"{home_team_name} vs {away_team_name}",
            k_draw_parameter, eta_home_advantage
        )

        # Update Domestic Club ELOs
        if is_same_nation:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_club, updated_away_club,
                'elo_domestic_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update Intraleague Club ELOs
        if is_same_league:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_club, updated_away_club,
                'elo_intraleague_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Update International Club ELOs
        if is_international:
            updated_home_club, updated_away_club = calculate_elo_ratings(
                self.conn, home_score, away_score,
                updated_home_club, updated_away_club,
                'elo_international_k', k_values, f"{home_team_name} vs {away_team_name}",
                k_draw_parameter, eta_home_advantage
            )

        # Determine match result
        if home_score > away_score:
            result = 'home_wins'
        elif home_score < away_score:
            result = 'away_wins'
        else:
            result = 'draw_wins' 
        
        competition_id_str = str(competition_id)

        self.counts['combined_leagues'][result] += 1
        self.counts['combined_leagues']['count'] += 1

        # Ensure the league count dict exists
        if competition_id_str in self.counts:
            self.counts[competition_id_str][result] += 1
            self.counts[competition_id_str]['count'] += 1
        else:
            raise ValueError(f"Competition ID {competition_id_str} not found in counts. Did you forget to initialize it?")

        # Update in-memory ELO dictionaries
        self.club_elos[home_team_id] = updated_home_club
        self.club_elos[away_team_id] = updated_away_club
        self.nation_elos[home_team_domestic_country] = updated_home_nation
        self.nation_elos[away_team_domestic_country] = updated_away_nation
        self.league_elos[home_team_domestic_league_id] = updated_home_league
        self.league_elos[away_team_domestic_league_id] = updated_away_league
        self.continent_elos[home_team_continent] = updated_home_continent
        self.continent_elos[away_team_continent] = updated_away_continent

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mode == 'training':
            # Save to regular training tables
            save_elo_history_bulk(self.conn, self.elo_history)
            save_updated_elos_bulk(self.conn, self.club_elos, self.nation_elos, self.league_elos, self.continent_elos)
            save_updated_counts(self.conn, self.counts)
        elif self.mode == 'inference':
            # Save to future/inference tables - you'll need to create these functions
            save_elo_future_bulk(self.conn, self.elo_history)
            # Don't save updated ELOs or counts since we didn't update them

        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
