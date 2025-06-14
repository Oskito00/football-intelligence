from typing import Dict, List, Any, Tuple
import psycopg2
from collections import deque
import numpy as np
from datetime import datetime, timedelta
import json


class H2HManager:
    def __init__(self, conn, matches, mode='training'):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'
        
        # Cache for H2H stats during batch processing
        self._h2h_stats_cache = {}  # Dict[Tuple[int, int], Dict]
        
        # Store H2H features for saving to database
        self.h2h_features = []
        
        # Track which team pairs we've processed
        self.processed_pairs = set()

    def __enter__(self):
        """Load H2H stats for all team pairs in the batch"""
        # Extract unique team pairs from the batch
        team_pairs = set()
        for match in self.matches:
            home_id = match['home_team_id']
            away_id = match['away_team_id']
            # Store pairs in a consistent order (smaller ID first)
            team_pairs.add(tuple(sorted([home_id, away_id])))
        
        # Load H2H stats for all pairs in the batch
        self._load_h2h_stats(team_pairs)
        return self

    def _load_h2h_stats(self, team_pairs: set):
        """Load H2H stats for all team pairs in the batch"""
        query = """
            SELECT 
                h.team1_id, h.team2_id,
                h.team1_name, h.team2_name,
                h.total_matches, h.team1_wins, h.team2_wins, h.draws,
                h.team1_goals, h.team2_goals,
                h.recent_matches,
                h.last_updated
            FROM h2h_stats h
            WHERE (h.team1_id, h.team2_id) = ANY(%s)
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (list(team_pairs),))
            results = cur.fetchall()
        
        # Initialize cache with loaded data
        for row in results:
            pair_key = (row['team1_id'], row['team2_id'])
            
            # Handle recent_matches - it might be a list, JSON string, or None
            recent_matches = row['recent_matches']
            if recent_matches is None:
                recent_matches = []
            elif isinstance(recent_matches, str):
                recent_matches = json.loads(recent_matches)
            
            self._h2h_stats_cache[pair_key] = {
                'team1_id': row['team1_id'],
                'team2_id': row['team2_id'],
                'team1_name': row['team1_name'],
                'team2_name': row['team2_name'],
                'total_matches': row['total_matches'],
                'team1_wins': row['team1_wins'],
                'team2_wins': row['team2_wins'],
                'draws': row['draws'],
                'team1_goals': row['team1_goals'],
                'team2_goals': row['team2_goals'],
                'recent_matches': recent_matches,
                'last_updated': row['last_updated']
            }
        
        # Initialize cache for pairs not found in database
        for pair in team_pairs:
            if pair not in self._h2h_stats_cache:
                # Get team names from the matches
                team1_name = None
                team2_name = None
                for match in self.matches:
                    if match['home_team_id'] == pair[0]:
                        team1_name = match['home_team_name']
                    elif match['away_team_id'] == pair[0]:
                        team1_name = match['away_team_name']
                    if match['home_team_id'] == pair[1]:
                        team2_name = match['home_team_name']
                    elif match['away_team_id'] == pair[1]:
                        team2_name = match['away_team_name']
                    if team1_name and team2_name:
                        break
                
                self._h2h_stats_cache[pair] = {
                    'team1_id': pair[0],
                    'team2_id': pair[1],
                    'team1_name': team1_name or f"Team {pair[0]}",
                    'team2_name': team2_name or f"Team {pair[1]}",
                    'total_matches': 0,
                    'team1_wins': 0,
                    'team2_wins': 0,
                    'draws': 0,
                    'team1_goals': 0,
                    'team2_goals': 0,
                    'recent_matches': [],
                    'last_updated': datetime.now()
                }

    def _calculate_h2h_features(self, h2h_stats: Dict, home_id: int, away_id: int) -> Dict[str, float]:
        """Calculate H2H features from the stats"""
        features = {
            'h2h_draws_last_3': -1.0,
            'h2h_draws_last_5': -1.0,
            'h2h_draws_last_10': -1.0,
            'h2h_home_wins_last_3': -1.0,
            'h2h_home_wins_last_5': -1.0,
            'h2h_home_wins_last_10': -1.0,
            'h2h_away_wins_last_3': -1.0,
            'h2h_away_wins_last_5': -1.0,
            'h2h_away_wins_last_10': -1.0,
            'h2h_avg_total_goals': -1.0,
            'h2h_avg_goal_diff': -1.0,
            'h2h_home_goals_avg_last_3': -1.0,
            'h2h_home_goals_avg_last_5': -1.0,
            'h2h_home_goals_avg_last_10': -1.0,
            'h2h_away_goals_avg_last_3': -1.0,
            'h2h_away_goals_avg_last_5': -1.0,
            'h2h_away_goals_avg_last_10': -1.0,
            'h2h_both_teams_scored_rate': -1.0,
            'h2h_zero_goal_rate': -1.0
        }
        
        # Overall H2H features
        total_matches = h2h_stats['total_matches']
        if total_matches > 0:
            features['h2h_avg_total_goals'] = (h2h_stats['team1_goals'] + h2h_stats['team2_goals']) / total_matches
            features['h2h_avg_goal_diff'] = (h2h_stats['team1_goals'] - h2h_stats['team2_goals']) / total_matches
        
        # Recent matches features (last 3, 5, 10)
        recent_matches = h2h_stats['recent_matches']
        for window in [3, 5, 10]:
            if len(recent_matches) >= window:
                window_matches = recent_matches[-window:]
                
                # Calculate recent stats
                draws = sum(1 for m in window_matches if m['home_score'] == m['away_score'])
                home_wins = sum(1 for m in window_matches if m['home_score'] > m['away_score'])
                away_wins = sum(1 for m in window_matches if m['home_score'] < m['away_score'])
                
                # Calculate goal averages
                home_goals = sum(m['home_score'] for m in window_matches)
                away_goals = sum(m['away_score'] for m in window_matches)
                
                # Calculate both teams scored and zero goals
                both_scored = sum(1 for m in window_matches if m['home_score'] > 0 and m['away_score'] > 0)
                zero_goals = sum(1 for m in window_matches if m['home_score'] == 0 and m['away_score'] == 0)
                
                # Add features
                features[f'h2h_draws_last_{window}'] = draws / window
                features[f'h2h_home_wins_last_{window}'] = home_wins / window
                features[f'h2h_away_wins_last_{window}'] = away_wins / window
                features[f'h2h_home_goals_avg_last_{window}'] = home_goals / window
                features[f'h2h_away_goals_avg_last_{window}'] = away_goals / window
                features['h2h_both_teams_scored_rate'] = both_scored / window
                features['h2h_zero_goal_rate'] = zero_goals / window
        
        return features

    def process_match(self, match: Dict[str, Any]):
        """Process a single match and update H2H stats"""
        match_id = match['match_id']
        home_id = match['home_team_id']
        away_id = match['away_team_id']
        
        # Get the team pair key (sorted)
        pair_key = tuple(sorted([home_id, away_id]))
        
        # Get H2H stats from cache
        h2h_stats = self._h2h_stats_cache[pair_key]
        
        # For inference mode, we don't have scores
        if self.mode == 'inference':
            home_score = None
            away_score = None
        else:
            home_score = match['home_score']
            away_score = match['away_score']
        
        # Calculate H2H features
        h2h_features = self._calculate_h2h_features(h2h_stats, home_id, away_id)
        
        # Store features
        self.h2h_features.append({
            'match_id': match_id,
            **h2h_features
        })
        
        # Update H2H stats in cache (only in training mode)
        if self.mode == 'training' and home_score is not None and away_score is not None:
            # Update aggregated stats
            h2h_stats['total_matches'] += 1
            
            # Determine which team is team1 and which is team2 based on the pair_key
            team1_id, team2_id = pair_key
            
            # Update goals based on which team is team1/team2
            if team1_id == home_id:
                h2h_stats['team1_goals'] += home_score
                h2h_stats['team2_goals'] += away_score
            else:
                h2h_stats['team1_goals'] += away_score
                h2h_stats['team2_goals'] += home_score
            
            # Update wins/draws based on which team is team1/team2
            if home_score == away_score:
                h2h_stats['draws'] += 1
            elif (home_score > away_score and team1_id == home_id) or \
                 (away_score > home_score and team1_id == away_id):
                h2h_stats['team1_wins'] += 1
            else:
                h2h_stats['team2_wins'] += 1
            
            # Update recent matches
            recent_match = {
                'match_id': match_id,
                'start_time': match['start_time'],
                'home_score': home_score,
                'away_score': away_score
            }
            h2h_stats['recent_matches'].append(recent_match)
            if len(h2h_stats['recent_matches']) > 10:
                h2h_stats['recent_matches'].pop(0)
            
            h2h_stats['last_updated'] = datetime.now()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save H2H features and update H2H stats"""
        # Save H2H features to h2h_history
        if self.h2h_features:
            with self.conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO h2h_history (
                        match_id,
                        h2h_draws_last_3, h2h_draws_last_5, h2h_draws_last_10,
                        h2h_home_wins_last_3, h2h_home_wins_last_5, h2h_home_wins_last_10,
                        h2h_away_wins_last_3, h2h_away_wins_last_5, h2h_away_wins_last_10,
                        h2h_avg_total_goals, h2h_avg_goal_diff,
                        h2h_home_goals_avg_last_3, h2h_home_goals_avg_last_5, h2h_home_goals_avg_last_10,
                        h2h_away_goals_avg_last_3, h2h_away_goals_avg_last_5, h2h_away_goals_avg_last_10,
                        h2h_both_teams_scored_rate, h2h_zero_goal_rate
                    )
                    VALUES (
                        %(match_id)s,
                        %(h2h_draws_last_3)s, %(h2h_draws_last_5)s, %(h2h_draws_last_10)s,
                        %(h2h_home_wins_last_3)s, %(h2h_home_wins_last_5)s, %(h2h_home_wins_last_10)s,
                        %(h2h_away_wins_last_3)s, %(h2h_away_wins_last_5)s, %(h2h_away_wins_last_10)s,
                        %(h2h_avg_total_goals)s, %(h2h_avg_goal_diff)s,
                        %(h2h_home_goals_avg_last_3)s, %(h2h_home_goals_avg_last_5)s, %(h2h_home_goals_avg_last_10)s,
                        %(h2h_away_goals_avg_last_3)s, %(h2h_away_goals_avg_last_5)s, %(h2h_away_goals_avg_last_10)s,
                        %(h2h_both_teams_scored_rate)s, %(h2h_zero_goal_rate)s
                    )
                    ON CONFLICT (match_id) DO UPDATE
                    SET h2h_draws_last_3 = EXCLUDED.h2h_draws_last_3,
                        h2h_draws_last_5 = EXCLUDED.h2h_draws_last_5,
                        h2h_draws_last_10 = EXCLUDED.h2h_draws_last_10,
                        h2h_home_wins_last_3 = EXCLUDED.h2h_home_wins_last_3,
                        h2h_home_wins_last_5 = EXCLUDED.h2h_home_wins_last_5,
                        h2h_home_wins_last_10 = EXCLUDED.h2h_home_wins_last_10,
                        h2h_away_wins_last_3 = EXCLUDED.h2h_away_wins_last_3,
                        h2h_away_wins_last_5 = EXCLUDED.h2h_away_wins_last_5,
                        h2h_away_wins_last_10 = EXCLUDED.h2h_away_wins_last_10,
                        h2h_avg_total_goals = EXCLUDED.h2h_avg_total_goals,
                        h2h_avg_goal_diff = EXCLUDED.h2h_avg_goal_diff,
                        h2h_home_goals_avg_last_3 = EXCLUDED.h2h_home_goals_avg_last_3,
                        h2h_home_goals_avg_last_5 = EXCLUDED.h2h_home_goals_avg_last_5,
                        h2h_home_goals_avg_last_10 = EXCLUDED.h2h_home_goals_avg_last_10,
                        h2h_away_goals_avg_last_3 = EXCLUDED.h2h_away_goals_avg_last_3,
                        h2h_away_goals_avg_last_5 = EXCLUDED.h2h_away_goals_avg_last_5,
                        h2h_away_goals_avg_last_10 = EXCLUDED.h2h_away_goals_avg_last_10,
                        h2h_both_teams_scored_rate = EXCLUDED.h2h_both_teams_scored_rate,
                        h2h_zero_goal_rate = EXCLUDED.h2h_zero_goal_rate
                """, self.h2h_features)
        
        # Update H2H stats (only in training mode)
        if self.mode == 'training':
            with self.conn.cursor() as cur:
                # Convert the stats to a format suitable for database insertion
                stats_to_insert = []
                for pair, data in self._h2h_stats_cache.items():
                    # Convert recent matches to JSON-serializable format
                    recent_matches = []
                    for match in data['recent_matches']:
                        recent_matches.append({
                            'match_id': match['match_id'],
                            'start_time': match['start_time'].isoformat() if isinstance(match['start_time'], datetime) else match['start_time'],
                            'home_score': match['home_score'],
                            'away_score': match['away_score']
                        })
                    
                    stats_dict = {
                        'team1_id': pair[0],
                        'team2_id': pair[1],
                        'team1_name': data['team1_name'],
                        'team2_name': data['team2_name'],
                        'total_matches': data['total_matches'],
                        'team1_wins': data['team1_wins'],
                        'team2_wins': data['team2_wins'],
                        'draws': data['draws'],
                        'team1_goals': data['team1_goals'],
                        'team2_goals': data['team2_goals'],
                        'recent_matches': json.dumps(recent_matches),
                        'last_updated': data['last_updated'].isoformat() if isinstance(data['last_updated'], datetime) else data['last_updated']
                    }
                    stats_to_insert.append(stats_dict)
                
                cur.executemany("""
                    INSERT INTO h2h_stats (
                        team1_id, team2_id,
                        team1_name, team2_name,
                        total_matches, team1_wins, team2_wins, draws,
                        team1_goals, team2_goals,
                        recent_matches,
                        last_updated
                    )
                    VALUES (
                        %(team1_id)s, %(team2_id)s,
                        %(team1_name)s, %(team2_name)s,
                        %(total_matches)s, %(team1_wins)s, %(team2_wins)s, %(draws)s,
                        %(team1_goals)s, %(team2_goals)s,
                        %(recent_matches)s,
                        %(last_updated)s
                    )
                    ON CONFLICT (team1_id, team2_id) DO UPDATE
                    SET team1_name = EXCLUDED.team1_name,
                        team2_name = EXCLUDED.team2_name,
                        total_matches = EXCLUDED.total_matches,
                        team1_wins = EXCLUDED.team1_wins,
                        team2_wins = EXCLUDED.team2_wins,
                        draws = EXCLUDED.draws,
                        team1_goals = EXCLUDED.team1_goals,
                        team2_goals = EXCLUDED.team2_goals,
                        recent_matches = EXCLUDED.recent_matches,
                        last_updated = EXCLUDED.last_updated
                """, stats_to_insert)
        
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit() 