"""
Feature loader for result prediction model
Loads and combines features from multiple tables for match outcome prediction
"""

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from ml_pipeline.features.base_feature_loader import BaseFeatureLoader


class ResultFeatureLoader(BaseFeatureLoader):
    """
    Loads features for football match result prediction
    Combines ELO ratings, fatigue metrics, stage of season, formations, etc.
    Supports dynamic feature loading based on model requirements
    """
    
    def __init__(self, conn, config: Dict[str, Any]):
        super().__init__(conn, config)
        self.feature_requirements = config.get('feature_requirements', {})
        
    def get_required_tables(self) -> List[str]:
        """Return list of required database tables"""
        base_tables = [
            'matches',
            'elo_history',
            # 'fatigue_history',
            'stage_of_season_history',
            'match_info_history'
        ]
        
        # Add formation_history only if formations are required
        if self.feature_requirements.get('formations', False):
            base_tables.append('formation_history')
            
        return base_tables
    
    def load_features(self, where_clause: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load and prepare features for result prediction
        
        Args:
            where_clause: Optional SQL WHERE clause to filter data
            limit: Optional limit on number of records
            
        Returns:
            DataFrame with features and match_id as index
        """
        self.logger.info(f"Loading result prediction features (variant: {self.config.get('feature_requirements', {}).get('formations', 'unknown')})")
        
        # Build query dynamically based on required features
        query_parts = self._build_dynamic_query()
        
        base_query = f"""
            SELECT 
                m.match_id,
                {query_parts['select_fields']}
            FROM matches m
            {query_parts['joins']}
            WHERE m.home_score IS NOT NULL 
            AND m.away_score IS NOT NULL
        """
        
        # Add additional filters
        if where_clause:
            base_query += f" AND {where_clause}"
        
        # Add limit
        if limit:
            base_query += f" LIMIT {limit}"
        
        # Execute query
        features_df = self.execute_query(base_query)
        
        if features_df.empty:
            self.logger.warning("No features loaded")
            return pd.DataFrame()
        
        # Set match_id as index
        features_df.set_index('match_id', inplace=True)
        
        # Engineer additional features based on what's available
        features_df = self._engineer_features_dynamic(features_df)
        
        self.logger.info(f"Loaded {len(features_df)} feature samples with {len(features_df.columns)} features")
        return features_df
    
    def _build_dynamic_query(self) -> Dict[str, str]:
        """Build query parts based on feature requirements"""
        select_fields = []
        joins = []
        
        # Always include comprehensive ELO features
        if 'elo_history' in self.feature_tables:
            select_fields.extend([
                "-- CORE ELO FEATURES (Club ELOs - all K values)",
                "eh.home_team_elo_K5, eh.away_team_elo_K5",
                "eh.home_team_elo_K10, eh.away_team_elo_K10",
                "eh.home_team_elo_K20, eh.away_team_elo_K20", 
                "eh.home_team_elo_K30, eh.away_team_elo_K30",
                "eh.home_team_elo_K40, eh.away_team_elo_K40",
                "eh.home_team_elo_K80, eh.away_team_elo_K80",
                "",
                "-- HOME/AWAY SPECIFIC ELO RATINGS",
                "eh.home_team_elo_home_matches_K5, eh.away_team_elo_home_matches_K5",
                "eh.home_team_elo_home_matches_K10, eh.away_team_elo_home_matches_K10",
                "eh.home_team_elo_home_matches_K20, eh.away_team_elo_home_matches_K20",
                "eh.home_team_elo_home_matches_K30, eh.away_team_elo_home_matches_K30",
                "eh.home_team_elo_home_matches_K40, eh.away_team_elo_home_matches_K40",
                "eh.home_team_elo_home_matches_K80, eh.away_team_elo_home_matches_K80",
                "",
                "eh.home_team_elo_away_matches_K5, eh.away_team_elo_away_matches_K5",
                "eh.home_team_elo_away_matches_K10, eh.away_team_elo_away_matches_K10",
                "eh.home_team_elo_away_matches_K20, eh.away_team_elo_away_matches_K20",
                "eh.home_team_elo_away_matches_K30, eh.away_team_elo_away_matches_K30",
                "eh.home_team_elo_away_matches_K40, eh.away_team_elo_away_matches_K40",
                "eh.home_team_elo_away_matches_K80, eh.away_team_elo_away_matches_K80",
                "",
                "-- DOMESTIC COMPETITION ELO RATINGS",
                "eh.home_team_elo_domestic_K5, eh.away_team_elo_domestic_K5",
                "eh.home_team_elo_domestic_K10, eh.away_team_elo_domestic_K10",
                "eh.home_team_elo_domestic_K20, eh.away_team_elo_domestic_K20",
                "eh.home_team_elo_domestic_K30, eh.away_team_elo_domestic_K30",
                "eh.home_team_elo_domestic_K40, eh.away_team_elo_domestic_K40",
                "eh.home_team_elo_domestic_K80, eh.away_team_elo_domestic_K80",
                "",
                "-- INTRA-LEAGUE ELO RATINGS",
                "eh.home_team_elo_intraleague_K5, eh.away_team_elo_intraleague_K5",
                "eh.home_team_elo_intraleague_K10, eh.away_team_elo_intraleague_K10",
                "eh.home_team_elo_intraleague_K20, eh.away_team_elo_intraleague_K20",
                "eh.home_team_elo_intraleague_K30, eh.away_team_elo_intraleague_K30",
                "eh.home_team_elo_intraleague_K40, eh.away_team_elo_intraleague_K40",
                "eh.home_team_elo_intraleague_K80, eh.away_team_elo_intraleague_K80",
                "",
                "-- INTERNATIONAL ELO RATINGS",
                "eh.home_team_elo_international_K5, eh.away_team_elo_international_K5",
                "eh.home_team_elo_international_K10, eh.away_team_elo_international_K10",
                "eh.home_team_elo_international_K20, eh.away_team_elo_international_K20",
                "eh.home_team_elo_international_K30, eh.away_team_elo_international_K30",
                "eh.home_team_elo_international_K40, eh.away_team_elo_international_K40",
                "eh.home_team_elo_international_K80, eh.away_team_elo_international_K80",
                "",
                "-- NATION ELO RATINGS",
                "eh.home_team_nation_elo_K5, eh.away_team_nation_elo_K5",
                "eh.home_team_nation_elo_K10, eh.away_team_nation_elo_K10",
                "eh.home_team_nation_elo_K20, eh.away_team_nation_elo_K20",
                "eh.home_team_nation_elo_K30, eh.away_team_nation_elo_K30",
                "eh.home_team_nation_elo_K40, eh.away_team_nation_elo_K40",
                "eh.home_team_nation_elo_K80, eh.away_team_nation_elo_K80",
                "",
                "-- LEAGUE ELO RATINGS",
                "eh.home_team_league_domestic_elo_K5, eh.away_team_league_domestic_elo_K5",
                "eh.home_team_league_domestic_elo_K10, eh.away_team_league_domestic_elo_K10",
                "eh.home_team_league_domestic_elo_K20, eh.away_team_league_domestic_elo_K20",
                "eh.home_team_league_domestic_elo_K30, eh.away_team_league_domestic_elo_K30",
                "eh.home_team_league_domestic_elo_K40, eh.away_team_league_domestic_elo_K40",
                "eh.home_team_league_domestic_elo_K80, eh.away_team_league_domestic_elo_K80",
                "",
                "eh.home_team_league_continental_elo_K5, eh.away_team_league_continental_elo_K5",
                "eh.home_team_league_continental_elo_K10, eh.away_team_league_continental_elo_K10",
                "eh.home_team_league_continental_elo_K20, eh.away_team_league_continental_elo_K20",
                "eh.home_team_league_continental_elo_K30, eh.away_team_league_continental_elo_K30",
                "eh.home_team_league_continental_elo_K40, eh.away_team_league_continental_elo_K40",
                "eh.home_team_league_continental_elo_K80, eh.away_team_league_continental_elo_K80",
                "",
                "-- ELO PARAMETERS",
                "eh.k_draw_parameter",
                "eh.eta_home_advantage",
                "",
                "-- TEAM IDs",
                "eh.home_team_id",
                "eh.away_team_id"
            ])
            joins.append("LEFT JOIN elo_history eh ON m.match_id = eh.match_id")
        
        # TODO: Add fatigue features when ready
        # Always include comprehensive fatigue features
        # if 'fatigue_history' in self.feature_tables:
        #     select_fields.extend([
        #         "-- FATIGUE FEATURES",
        #         "fh.home_team_time_since_last_match",
        #         "fh.away_team_time_since_last_match",
        #         # ... all the fatigue fields
        #     ])
        #     joins.append("LEFT JOIN fatigue_history fh ON m.match_id = fh.match_id")
        
        # Stage of season
        if 'stage_of_season_history' in self.feature_tables:
            select_fields.extend([
                "-- STAGE OF SEASON",
                "ssh.stage_of_season",
                "ssh.stage_of_season_category"
            ])
            joins.append("LEFT JOIN stage_of_season_history ssh ON m.match_id = ssh.match_id")
        
        # Conditional formations - only if required
        if (self.feature_requirements.get('formations', False) and 
            'formation_history' in self.feature_tables):
            select_fields.extend([
                "-- FORMATION FEATURES",
                "foh.home_team_formation",
                "foh.away_team_formation"
            ])
            joins.append("LEFT JOIN formation_history foh ON m.match_id = foh.match_id")
        
        # Match info
        if 'match_info_history' in self.feature_tables:
            select_fields.extend([
                "-- MATCH INFO",
                "mih.competition_id",
                "mih.competition_name",
                "mih.competition_country"
            ])
            joins.append("LEFT JOIN match_info_history mih ON m.match_id = mih.match_id")
        
        return {
            'select_fields': ',\n                '.join([field for field in select_fields if field]),
            'joins': '\n            '.join(joins)
        }

    def load_targets(self, match_ids: Optional[List[int]] = None) -> pd.Series:
        """
        Load target variable (match result)
        
        Args:
            match_ids: Optional list of match IDs to filter
            
        Returns:
            Series with targets and match_id as index
        """
        if match_ids is None:
            query = """
                SELECT match_id, 
                       CASE 
                           WHEN home_score > away_score THEN 'home_win'
                           WHEN home_score < away_score THEN 'away_win'
                           ELSE 'draw'
                       END as result
                FROM matches
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            """
            params = None
        else:
            placeholders = ', '.join(['%s'] * len(match_ids))
            query = f"""
                SELECT match_id, 
                       CASE 
                           WHEN home_score > away_score THEN 'home_win'
                           WHEN home_score < away_score THEN 'away_win'
                           ELSE 'draw'
                       END as result
                FROM matches
                WHERE match_id IN ({placeholders})
                AND home_score IS NOT NULL AND away_score IS NOT NULL
            """
            params = tuple(match_ids)
        
        targets_df = self.execute_query(query, params)
        
        if targets_df.empty:
            return pd.Series(dtype='object')
        
        targets_series = targets_df.set_index('match_id')['result']
        
        self.logger.info(f"Loaded {len(targets_series)} target labels")
        return targets_series
    
    def _engineer_features_dynamic(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer additional features based on available columns
        
        Args:
            df: Raw features DataFrame
            
        Returns:
            DataFrame with engineered features
        """
        self.logger.info("Engineering features dynamically")
        
        # Always do ELO differences for all available ELO types
        self._create_elo_differences(df)
        
        # TODO: Add when fatigue features ready
        # Always do fatigue differences  
        # self._create_fatigue_differences(df)
        
        # Only do formation features if formations are available and required
        if (self.feature_requirements.get('formations', False) and 
            'home_team_formation' in df.columns):
            self._create_formation_features(df)
        
        # Competition encoding
        if 'competition_id' in df.columns:
            df = pd.get_dummies(df, columns=['competition_id'], prefix='comp')
        
        return df
    
    def _create_elo_differences(self, df: pd.DataFrame) -> None:
        """Create ELO differences for all available ELO types and K values"""
        # All ELO types and K values
        elo_types = [
            'elo', 'elo_home_matches', 'elo_away_matches', 'elo_domestic', 
            'elo_intraleague', 'elo_international', 'nation_elo',
            'league_domestic_elo', 'league_continental_elo'
        ]
        k_values = [5, 10, 20, 30, 40, 80]
        
        # Create ELO differences for all types and K values
        for elo_type in elo_types:
            for k in k_values:
                home_col = f'home_team_{elo_type}_K{k}'
                away_col = f'away_team_{elo_type}_K{k}'
                if home_col in df.columns and away_col in df.columns:
                    df[f'{elo_type}_diff_K{k}'] = df[home_col] - df[away_col]

    def _create_fatigue_differences(self, df: pd.DataFrame) -> None:
        """Create fatigue differences for all available time windows"""
        # TODO: Implement when fatigue features are ready
        pass
        # Original implementation commented out:
        # if ('home_team_time_since_last_match' in df.columns and 
        #     'away_team_time_since_last_match' in df.columns):
        #     df['time_since_last_match_diff'] = (
        #         df['home_team_time_since_last_match'] - df['away_team_time_since_last_match']
        #     )
        # ... rest of fatigue logic

    def _create_formation_features(self, df: pd.DataFrame) -> None:
        """Create formation features only if formations available"""
        self.logger.info("Creating formation features")
        
        # One-hot encode common formations
        common_formations = ['4-4-2', '4-3-3', '3-5-2', '4-2-3-1', '3-4-3', '4-5-1', '5-3-2']
        
        for formation in common_formations:
            safe_formation = formation.replace("-", "_")
            df[f'home_formation_{safe_formation}'] = (
                df['home_team_formation'] == formation
            ).astype(int)
            df[f'away_formation_{safe_formation}'] = (
                df['away_team_formation'] == formation
            ).astype(int)
        
        # Create formation interaction features if enabled
        feature_engineering = self.config.get('feature_engineering', {})
        if feature_engineering.get('create_formation_interactions', False):
            # Example: Formation aggressiveness score
            formation_scores = {
                '4-4-2': 0.5, '4-3-3': 0.7, '3-5-2': 0.4, 
                '4-2-3-1': 0.6, '3-4-3': 0.8, '4-5-1': 0.3, '5-3-2': 0.2
            }
            
            df['home_formation_aggressiveness'] = df['home_team_formation'].map(formation_scores).fillna(0.5)
            df['away_formation_aggressiveness'] = df['away_team_formation'].map(formation_scores).fillna(0.5)
            df['formation_aggressiveness_diff'] = df['home_formation_aggressiveness'] - df['away_formation_aggressiveness']
        
        # Drop original formation columns as they're now encoded
        df.drop(['home_team_formation', 'away_team_formation'], axis=1, inplace=True, errors='ignore')
        
    def _encode_formations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legacy method - use _create_formation_features instead"""
        self._create_formation_features(df)
        return df 