from typing import Dict, List, Any
import psycopg2
from collections import deque
import numpy as np
from datetime import datetime, timedelta
import json

from utils.parsing.list import extract_team_ids

class FormManager:
    # Class-level cache to persist across batches
    _team_form_cache = {}  # Dict[team_id, deque(maxlen=10)]
    
    def __init__(self, conn, matches, mode='training', elo_manager=None):
        self.conn = conn
        self.matches = matches
        self.mode = mode  # 'training' or 'inference'
        self.elo_manager = elo_manager  # Reference to EloManager instance

        # Store form history for saving to database
        self.form_history = []
        
        # Track which teams we've processed in this batch
        self.processed_teams = set()

        # New list to store matches for batch update
        self._matches_to_cache = []

    def __enter__(self):
        """Load recent matches for all teams in the batch"""
        # Extract unique team IDs from the batch
        team_ids = extract_team_ids(self.matches)
        
        # Load form data for teams not in cache
        teams_to_load = set(team_ids) - set(self._team_form_cache.keys())
        if teams_to_load:
            self._load_team_form_data(teams_to_load)
        
        return self

    def _load_team_form_data(self, team_ids: set):
        """Load recent matches for teams not in cache"""
        query = """
            WITH team_matches AS (
                SELECT 
                    m.match_id,
                    m.start_time,
                    m.home_team_id,
                    m.away_team_id,
                    m.home_score,
                    m.away_score,
                    m.home_team_elo,
                    m.away_team_elo,
                    m.home_team_international_elo,
                    m.away_team_international_elo
                FROM form_matches_cache m
                WHERE (m.home_team_id = ANY(%s) OR m.away_team_id = ANY(%s))
                ORDER BY m.start_time DESC
            )
            SELECT * FROM team_matches
            ORDER BY start_time DESC
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (list(team_ids), list(team_ids)))
            all_matches = cur.fetchall()
        
        # Process matches in chronological order (oldest first)
        for match in reversed(all_matches):
            home_team_id = match['home_team_id']
            away_team_id = match['away_team_id']
            
            # Add to home team's recent matches
            if home_team_id in team_ids and home_team_id not in self._team_form_cache:
                self._team_form_cache[home_team_id] = deque(maxlen=10)
            if home_team_id in team_ids:
                self._team_form_cache[home_team_id].append({
                    'goals_scored': match['home_score'],
                    'goals_conceded': match['away_score'],
                    'is_home': True,
                    'opponent_elo': match['away_team_elo'],
                    'opponent_international_elo': match['away_team_international_elo']
                })
            
            # Add to away team's recent matches
            if away_team_id in team_ids and away_team_id not in self._team_form_cache:
                self._team_form_cache[away_team_id] = deque(maxlen=10)
            if away_team_id in team_ids:
                self._team_form_cache[away_team_id].append({
                    'goals_scored': match['away_score'],
                    'goals_conceded': match['home_score'],
                    'is_home': False,
                    'opponent_elo': match['home_team_elo'],
                    'opponent_international_elo': match['home_team_international_elo']
                })

    def process_match(self, match: Dict[str, Any]):
        """Process a single match and update form data"""
        match_id = match['match_id']
        home_team_id = match['home_team_id']
        away_team_id = match['away_team_id']
        home_name = match.get('home_team_name', f"Team {home_team_id}")
        away_name = match.get('away_team_name', f"Team {away_team_id}")
        
        # Track processed teams
        self.processed_teams.add(home_team_id)
        self.processed_teams.add(away_team_id)
        
        # Initialize deques for both teams if they don't exist
        if home_team_id not in self._team_form_cache:
            self._team_form_cache[home_team_id] = deque(maxlen=10)
        if away_team_id not in self._team_form_cache:
            self._team_form_cache[away_team_id] = deque(maxlen=10)
        
        # For inference mode, we don't have scores
        if self.mode == 'inference':
            home_score = None
            away_score = None
        else:
            home_score = match['home_score']
            away_score = match['away_score']
        
        # Get current form data for both teams
        home_form = list(self._team_form_cache[home_team_id])
        away_form = list(self._team_form_cache[away_team_id])
        
        # Create form history record
        form_record = {
            'match_id': match_id,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'home_name': home_name,
            'away_name': away_name,
            'home_team_form': home_form,
            'away_team_form': away_form
        }
        self.form_history.append(form_record)
        
        # Update recent matches for both teams (only in training mode)
        if self.mode == 'training' and home_score is not None and away_score is not None:
            # Get current ELOs from EloManager cache
            home_elos = self.elo_manager.club_elos.get(home_team_id)
            away_elos = self.elo_manager.club_elos.get(away_team_id)
            
            if not home_elos or not away_elos:
                print(f"Warning: Missing ELOs for match {match_id}")
                print(f"Home team {home_team_id}: {home_elos}")
                print(f"Away team {away_team_id}: {away_elos}")
                return
            
            # Store match data for batch update
            self._matches_to_cache.append({
                'match_id': match_id,
                'start_time': match['start_time'],
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_name': home_name,
                'away_name': away_name,
                'home_score': home_score,
                'away_score': away_score,
                'home_team_elo': home_elos.get('elo_k20', 1500),
                'away_team_elo': away_elos.get('elo_k20', 1500),
                'home_team_international_elo': home_elos.get('elo_international_k20', 1500),
                'away_team_international_elo': away_elos.get('elo_international_k20', 1500)
            })
            
            # Update home team's recent matches
            self._team_form_cache[home_team_id].append({
                'goals_scored': home_score,
                'goals_conceded': away_score,
                'is_home': True,
                'opponent_elo': away_elos.get('elo_k20', 1500),
                'opponent_international_elo': away_elos.get('elo_international_k20', 1500)
            })
            
            # Update away team's recent matches
            self._team_form_cache[away_team_id].append({
                'goals_scored': away_score,
                'goals_conceded': home_score,
                'is_home': False,
                'opponent_elo': home_elos.get('elo_k20', 1500),
                'opponent_international_elo': home_elos.get('elo_international_k20', 1500)
            })

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save form history and update team form cache"""
        # Save form history
        if self.form_history:
            with self.conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO form_history (
                        match_id, home_team_id, away_team_id, 
                        home_name, away_name,
                        home_team_form, away_team_form
                    )
                    VALUES (
                        %(match_id)s, %(home_team_id)s, %(away_team_id)s,
                        %(home_name)s, %(away_name)s,
                        %(home_team_form)s, %(away_team_form)s
                    )
                    ON CONFLICT (match_id) DO UPDATE
                    SET home_team_form = EXCLUDED.home_team_form,
                        away_team_form = EXCLUDED.away_team_form
                """, [{
                    'match_id': record['match_id'],
                    'home_team_id': record['home_team_id'],
                    'away_team_id': record['away_team_id'],
                    'home_name': record['home_name'],
                    'away_name': record['away_name'],
                    'home_team_form': json.dumps(record['home_team_form']),
                    'away_team_form': json.dumps(record['away_team_form'])
                } for record in self.form_history])
        
        # Batch update form_matches_cache only in training mode
        if self.mode == 'training' and self._matches_to_cache:
            with self.conn.cursor() as cur:
                cur.executemany("""
                    INSERT INTO form_matches_cache (
                        match_id, start_time, home_team_id, away_team_id,
                        home_name, away_name,
                        home_score, away_score,
                        home_team_elo, away_team_elo,
                        home_team_international_elo, away_team_international_elo
                    )
                    VALUES (
                        %(match_id)s, %(start_time)s, %(home_team_id)s, %(away_team_id)s,
                        %(home_name)s, %(away_name)s,
                        %(home_score)s, %(away_score)s,
                        %(home_team_elo)s, %(away_team_elo)s,
                        %(home_team_international_elo)s, %(away_team_international_elo)s
                    )
                    ON CONFLICT (match_id) DO UPDATE
                    SET home_team_elo = EXCLUDED.home_team_elo,
                        away_team_elo = EXCLUDED.away_team_elo,
                        home_team_international_elo = EXCLUDED.home_team_international_elo,
                        away_team_international_elo = EXCLUDED.away_team_international_elo
                """, self._matches_to_cache)
        
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()