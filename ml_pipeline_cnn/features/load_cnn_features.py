"""
Feature loader for CNN-based football prediction model
Loads and transforms sequential match data (form and H2H) along with traditional features
"""

from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime

class CNNFeatureLoader:
    """
    Loads and transforms features for CNN-based football match prediction
    Handles sequential data (form and H2H) along with traditional features
    """
    
    def __init__(self, conn, config: dict, mode: str = 'training'):
        """
        Initialize feature loader
        
        Args:
            conn: Database connection
            config: Data configuration
            mode: 'training' or 'inference' - determines which tables to use
        """
        self.conn = conn
        self.config = config
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        
        # Set table names based on mode
        if mode == 'inference':
            self.elo_table = 'elo_future'
            self.form_history_table = 'form_history_future'
            self.h2h_history_table = 'h2h_history_future'
            self.stage_table = 'stage_of_season_future'
            self.match_info_table = 'match_info_future'
        else:  # training mode
            self.elo_table = 'elo_history'
            self.form_history_table = 'form_history'
            self.h2h_history_table = 'h2h_history'
            self.stage_table = 'stage_of_season_history'
            self.match_info_table = 'match_info_history'
        
        self.logger.info(f"Feature loader initialized for {mode} mode")
        
    def load_features(self, where_clause: Optional[str] = None, limit: Optional[int] = None) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        """
        Load and prepare features for CNN prediction
        
        Args:
            where_clause: Optional SQL WHERE clause to filter data
            limit: Optional limit on number of records
            
        Returns:
            Tuple of (traditional features, form sequences, h2h sequences)
        """
        self.logger.info("Loading features for CNN model")
        
        # Build query for traditional features
        query = self._build_traditional_features_query(where_clause, limit)
        
        # Execute query
        features_df = pd.read_sql_query(query, self.conn)
        
        if features_df.empty:
            self.logger.warning("No features loaded")
            return pd.DataFrame(), np.array([]), np.array([])
        
        # Set match_id as index
        features_df.set_index('match_id', inplace=True)
        
        # Load and transform sequential data
        form_sequences, h2h_sequences = self._load_sequential_data(features_df.index)
        
        # Convert timestamp to numeric features
        if 'start_time' in features_df.columns:
            features_df['start_time'] = pd.to_datetime(features_df['start_time'])
            features_df['hour_of_day'] = features_df['start_time'].dt.hour
            features_df['day_of_week'] = features_df['start_time'].dt.dayofweek
            features_df['month'] = features_df['start_time'].dt.month
            features_df['year'] = features_df['start_time'].dt.year
            features_df = features_df.drop('start_time', axis=1)
        
        # Handle categorical features - convert to numeric
        if 'competition_id' in features_df.columns:
            features_df['competition_id'] = pd.Categorical(features_df['competition_id']).codes
        if 'stage_of_season' in features_df.columns:
            features_df['stage_of_season'] = pd.Categorical(features_df['stage_of_season']).codes
        
        # Convert all columns to float32 for PyTorch
        features_df = features_df.astype('float32')
        
        self.logger.info(f"Loaded {len(features_df)} samples")
        self.logger.info(f"Form sequences shape: {form_sequences.shape}")
        self.logger.info(f"H2H sequences shape: {h2h_sequences.shape}")
        
        return features_df, form_sequences, h2h_sequences
    
    def _build_traditional_features_query(self, where_clause: Optional[str], limit: Optional[int]) -> str:
        """Build query for traditional features (ELO, etc.)"""
        query = f"""
            SELECT 
                eh.match_id,
                eh.start_time,
                eh.home_team_id,
                eh.away_team_id,
                
                -- CORE ELO RATINGS
                eh.home_team_elo_K5, eh.away_team_elo_K5,
                eh.home_team_elo_K10, eh.away_team_elo_K10,
                eh.home_team_elo_K20, eh.away_team_elo_K20,
                eh.home_team_elo_K30, eh.away_team_elo_K30,
                eh.home_team_elo_K40, eh.away_team_elo_K40,
                eh.home_team_elo_K80, eh.away_team_elo_K80,
                
                -- HOME/AWAY SPECIFIC ELO RATINGS
                eh.home_team_elo_home_matches_K5, eh.away_team_elo_home_matches_K5,
                eh.home_team_elo_home_matches_K10, eh.away_team_elo_home_matches_K10,
                eh.home_team_elo_home_matches_K20, eh.away_team_elo_home_matches_K20,
                eh.home_team_elo_home_matches_K30, eh.away_team_elo_home_matches_K30,
                eh.home_team_elo_home_matches_K40, eh.away_team_elo_home_matches_K40,
                eh.home_team_elo_home_matches_K80, eh.away_team_elo_home_matches_K80,
                
                eh.home_team_elo_away_matches_K5, eh.away_team_elo_away_matches_K5,
                eh.home_team_elo_away_matches_K10, eh.away_team_elo_away_matches_K10,
                eh.home_team_elo_away_matches_K20, eh.away_team_elo_away_matches_K20,
                eh.home_team_elo_away_matches_K30, eh.away_team_elo_away_matches_K30,
                eh.home_team_elo_away_matches_K40, eh.away_team_elo_away_matches_K40,
                eh.home_team_elo_away_matches_K80, eh.away_team_elo_away_matches_K80,
                
                -- DOMESTIC COMPETITION ELO RATINGS
                eh.home_team_elo_domestic_K5, eh.away_team_elo_domestic_K5,
                eh.home_team_elo_domestic_K10, eh.away_team_elo_domestic_K10,
                eh.home_team_elo_domestic_K20, eh.away_team_elo_domestic_K20,
                eh.home_team_elo_domestic_K30, eh.away_team_elo_domestic_K30,
                eh.home_team_elo_domestic_K40, eh.away_team_elo_domestic_K40,
                eh.home_team_elo_domestic_K80, eh.away_team_elo_domestic_K80,
                
                -- INTRA-LEAGUE ELO RATINGS
                eh.home_team_elo_intraleague_K5, eh.away_team_elo_intraleague_K5,
                eh.home_team_elo_intraleague_K10, eh.away_team_elo_intraleague_K10,
                eh.home_team_elo_intraleague_K20, eh.away_team_elo_intraleague_K20,
                eh.home_team_elo_intraleague_K30, eh.away_team_elo_intraleague_K30,
                eh.home_team_elo_intraleague_K40, eh.away_team_elo_intraleague_K40,
                eh.home_team_elo_intraleague_K80, eh.away_team_elo_intraleague_K80,
                
                -- INTERNATIONAL ELO RATINGS
                eh.home_team_elo_international_K5, eh.away_team_elo_international_K5,
                eh.home_team_elo_international_K10, eh.away_team_elo_international_K10,
                eh.home_team_elo_international_K20, eh.away_team_elo_international_K20,
                eh.home_team_elo_international_K30, eh.away_team_elo_international_K30,
                eh.home_team_elo_international_K40, eh.away_team_elo_international_K40,
                eh.home_team_elo_international_K80, eh.away_team_elo_international_K80,
                
                -- NATION ELO RATINGS
                eh.home_team_nation_elo_K5, eh.away_team_nation_elo_K5,
                eh.home_team_nation_elo_K10, eh.away_team_nation_elo_K10,
                eh.home_team_nation_elo_K20, eh.away_team_nation_elo_K20,
                eh.home_team_nation_elo_K30, eh.away_team_nation_elo_K30,
                eh.home_team_nation_elo_K40, eh.away_team_nation_elo_K40,
                eh.home_team_nation_elo_K80, eh.away_team_nation_elo_K80,
                
                -- LEAGUE ELO RATINGS
                eh.home_team_league_domestic_elo_K5, eh.away_team_league_domestic_elo_K5,
                eh.home_team_league_domestic_elo_K10, eh.away_team_league_domestic_elo_K10,
                eh.home_team_league_domestic_elo_K20, eh.away_team_league_domestic_elo_K20,
                eh.home_team_league_domestic_elo_K30, eh.away_team_league_domestic_elo_K30,
                eh.home_team_league_domestic_elo_K40, eh.away_team_league_domestic_elo_K40,
                eh.home_team_league_domestic_elo_K80, eh.away_team_league_domestic_elo_K80,
                
                eh.home_team_league_continental_elo_K5, eh.away_team_league_continental_elo_K5,
                eh.home_team_league_continental_elo_K10, eh.away_team_league_continental_elo_K10,
                eh.home_team_league_continental_elo_K20, eh.away_team_league_continental_elo_K20,
                eh.home_team_league_continental_elo_K30, eh.away_team_league_continental_elo_K30,
                eh.home_team_league_continental_elo_K40, eh.away_team_league_continental_elo_K40,
                eh.home_team_league_continental_elo_K80, eh.away_team_league_continental_elo_K80,
                
                -- ELO PARAMETERS
                eh.k_draw_parameter,
                eh.eta_home_advantage,
                
                -- Stage of season
                ssh.stage_of_season,
                
                -- Match info
                mih.competition_id
            FROM {self.elo_table} eh
            INNER JOIN {self.stage_table} ssh ON eh.match_id = ssh.match_id
            INNER JOIN {self.match_info_table} mih ON eh.match_id = mih.match_id
        """
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if limit:
            query += f" LIMIT {limit}"
            
        return query
    
    def _load_sequential_data(self, match_ids: pd.Index) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load and transform sequential data (form and H2H)
        
        Args:
            match_ids: Index of match IDs to load data for
            
        Returns:
            Tuple of (form_sequences, h2h_sequences)
        """
        # Load form history
        form_query = f"""
            SELECT match_id, home_team_form, away_team_form
            FROM {self.form_history_table}
            WHERE match_id = ANY(%s)
        """
        form_df = pd.read_sql_query(form_query, self.conn, params=(list(match_ids),))
        form_df.set_index('match_id', inplace=True)
        
        # Load H2H history
        h2h_query = f"""
            SELECT match_id, raw_h2h_matches
            FROM {self.h2h_history_table}
            WHERE match_id = ANY(%s)
        """
        h2h_df = pd.read_sql_query(h2h_query, self.conn, params=(list(match_ids),))
        h2h_df.set_index('match_id', inplace=True)
        
        # Transform form sequences
        form_sequences = self._transform_form_sequences(form_df)
        
        # Transform H2H sequences
        h2h_sequences = self._transform_h2h_sequences(h2h_df)
        
        return form_sequences, h2h_sequences
    
    def _transform_form_sequences(self, form_df: pd.DataFrame) -> np.ndarray:
        """
        Transform form history into sequences for CNN
        
        Args:
            form_df: DataFrame with form history
            
        Returns:
            Array of shape (n_samples, 10, 4) containing:
            - home_goals_scored
            - home_goals_conceded
            - away_goals_scored
            - away_goals_conceded
        """
        sequences = []
        
        for match_id, row in form_df.iterrows():
            # Parse home team form
            home_form = row['home_team_form']
            if isinstance(home_form, str):
                home_form = json.loads(home_form)
            
            # Parse away team form
            away_form = row['away_team_form']
            if isinstance(away_form, str):
                away_form = json.loads(away_form)
            
            # Pad sequences to length 10
            home_form = self._pad_sequence(home_form, 10)
            away_form = self._pad_sequence(away_form, 10)
            
            # Combine home and away form
            match_sequence = np.array([
                [h['goals_scored'], h['goals_conceded'], 
                 a['goals_scored'], a['goals_conceded']]
                for h, a in zip(home_form, away_form)
            ])
            
            sequences.append(match_sequence)
        
        return np.array(sequences)
    
    def _transform_h2h_sequences(self, h2h_df: pd.DataFrame) -> np.ndarray:
        """
        Transform H2H history into sequences for CNN
        
        Args:
            h2h_df: DataFrame with H2H history
            
        Returns:
            Array of shape (n_samples, 10, 2) containing:
            - home_score
            - away_score
        """
        sequences = []
        
        for match_id, row in h2h_df.iterrows():
            # Parse H2H matches - handle both string and already parsed JSON
            h2h_matches = row['raw_h2h_matches']
            if isinstance(h2h_matches, str):
                h2h_matches = json.loads(h2h_matches)
            
            # Pad sequence to length 10
            h2h_matches = self._pad_sequence(h2h_matches, 10)
            
            # Create sequence
            match_sequence = np.array([
                [m['home_score'], m['away_score']]
                for m in h2h_matches
            ])
            
            sequences.append(match_sequence)
        
        return np.array(sequences)
    
    def _pad_sequence(self, sequence: List[Dict], length: int) -> List[Dict]:
        """
        Pad a sequence to the specified length
        
        Args:
            sequence: List of match dictionaries
            length: Desired sequence length
            
        Returns:
            Padded sequence
        """
        if len(sequence) >= length:
            return sequence[-length:]
        
        # Create padding match with -1 values to distinguish from actual 0 scores
        padding_match = {
            'goals_scored': -1,
            'goals_conceded': -1,
            'home_score': -1,
            'away_score': -1
        }
        
        # Pad sequence
        return [padding_match] * (length - len(sequence)) + sequence 