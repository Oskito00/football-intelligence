"""
Feature loader for result prediction model
Loads and combines features from multiple tables for match outcome prediction
"""

from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import json

from ml_pipeline.features.base_feature_loader import BaseFeatureLoader


class ResultFeatureLoader(BaseFeatureLoader):
    """
    Loads features for football match result prediction
    Combines ELO ratings, fatigue metrics, stage of season, formations, etc.
    Supports dynamic feature loading based on model requirements
    """
    
    def __init__(self, conn, config: dict, mode: str = 'training'):
        """
        Initialize feature loader
        
        Args:
            conn: Database connection
            config: Data configuration
            mode: 'training' or 'inference' - determines which tables to use
        """
        super().__init__(conn, config)
        self.mode = mode
        
        # Set table names based on mode
        if mode == 'inference':
            self.elo_table = 'elo_future'
            self.formation_table = 'formation_future'  # If it exists
            self.stage_table = 'stage_of_season_future'
            self.match_info_table = 'match_info_future'
            self.form_history_table = 'form_future'
            self.h2h_table = 'h2h_future'
        else:  # training mode
            self.elo_table = 'elo_history'
            self.formation_table = 'formation_history'
            self.stage_table = 'stage_of_season_history'
            self.match_info_table = 'match_info_history'
            self.form_history_table = 'form_history'
            self.h2h_table = 'h2h_history'
        
        self.logger.info(f"Feature loader initialized for {mode} mode using {self.elo_table}")
        
        self.feature_requirements = config.get('feature_requirements', {})
        
    def get_required_tables(self) -> List[str]:
        """Return list of required database tables"""
        base_tables = [
            'matches',
            'elo_history',
            'stage_of_season_history',
            'match_info_history',
            'form_history',
            'h2h_history'
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
        self.logger.info(f"Loading result prediction features (mode: {self.mode}, variant: {self.config.get('feature_requirements', {}).get('formations', 'unknown')})")
        
        # Build query dynamically based on required features and mode
        query_parts = self._build_dynamic_query()
        
        # Use the appropriate base table based on mode
        base_query = f"""
            SELECT 
                eh.match_id,
                eh.start_time,
                eh.home_team_name,
                eh.away_team_name,
                {query_parts['select_fields']}
            FROM {self.elo_table} eh
            {query_parts['joins']}
        """
        
        # Add additional filters if provided
        if where_clause:
            base_query += f" WHERE {where_clause}"
        
        # Add limit
        if limit:
            base_query += f" LIMIT {limit}"
        
        # Execute query (this already filters through the INNER JOINs)
        features_df = self.execute_query(base_query)
        
        if features_df.empty:
            self.logger.warning("No features loaded")
            return pd.DataFrame()
        
        # Store metadata for ONLY the filtered matches
        self.metadata_df = features_df[['match_id', 'start_time', 'home_team_name', 'away_team_name']].copy()
        
        # Set match_id as index
        features_df.set_index('match_id', inplace=True)
        
        # Drop metadata columns from features
        features_df = features_df.drop(columns=['start_time', 'home_team_name', 'away_team_name'])
        
        # Engineer additional features based on what's available
        features_df = self._engineer_features_dynamic(features_df)
        
        self.logger.info(f"Loaded {len(features_df)} feature samples with {len(features_df.columns)} features")
        return features_df
    
    def _build_dynamic_query(self) -> Dict[str, str]:
        """Build query parts based on feature requirements and mode"""
        select_fields = []
        joins = []
        
        # Get table alias for the base ELO table
        table_alias = 'eh'
        
        # Add form history - INNER JOIN with minimum form length check
        if self.form_history_table in self.feature_tables:
            select_fields.extend([
                "-- FORM HISTORY",
                "fh.home_team_form::jsonb as home_team_form",
                "fh.away_team_form::jsonb as away_team_form",
                "fh.draw_features::jsonb as draw_features"
            ])
            joins.append(f"""
                INNER JOIN {self.form_history_table} fh 
                ON {table_alias}.match_id = fh.match_id 
                AND jsonb_array_length(fh.home_team_form) >= 10
                AND jsonb_array_length(fh.away_team_form) >= 10
            """)
        
        # Add H2H features - INNER JOIN
        if self.h2h_table in self.feature_tables:
            select_fields.extend([
                "-- H2H FEATURES",
                "h2h.h2h_draws_last_3",
                "h2h.h2h_draws_last_5",
                "h2h.h2h_draws_last_10",
                "h2h.h2h_home_wins_last_3",
                "h2h.h2h_home_wins_last_5",
                "h2h.h2h_home_wins_last_10",
                "h2h.h2h_away_wins_last_3",
                "h2h.h2h_away_wins_last_5",
                "h2h.h2h_away_wins_last_10",
                "h2h.h2h_avg_total_goals",
                "h2h.h2h_avg_goal_diff",
                "h2h.h2h_home_goals_avg_last_3",
                "h2h.h2h_home_goals_avg_last_5",
                "h2h.h2h_home_goals_avg_last_10",
                "h2h.h2h_away_goals_avg_last_3",
                "h2h.h2h_away_goals_avg_last_5",
                "h2h.h2h_away_goals_avg_last_10",
                "h2h.h2h_both_teams_scored_rate",
                "h2h.h2h_zero_goal_rate"
            ])
            joins.append(f"""
                INNER JOIN {self.h2h_table} h2h 
                ON {table_alias}.match_id = h2h.match_id
            """)
        
        # Always include comprehensive ELO features (already in base table)
        select_fields.extend([
            "-- MATCH METADATA",
            f"{table_alias}.start_time",
            f"{table_alias}.home_team_name",
            f"{table_alias}.away_team_name",
            "",
            "-- CORE ELO FEATURES (Club ELOs - all K values)",
            # f"{table_alias}.home_team_elo_K5, {table_alias}.away_team_elo_K5",
            # f"{table_alias}.home_team_elo_K10, {table_alias}.away_team_elo_K10",
            f"{table_alias}.home_team_elo_K20, {table_alias}.away_team_elo_K20", 
            # f"{table_alias}.home_team_elo_K30, {table_alias}.away_team_elo_K30",
            # f"{table_alias}.home_team_elo_K40, {table_alias}.away_team_elo_K40",
            # f"{table_alias}.home_team_elo_K80, {table_alias}.away_team_elo_K80",
            "",
            "-- HOME/AWAY SPECIFIC ELO RATINGS",
            f"{table_alias}.home_team_elo_home_matches_K5, {table_alias}.away_team_elo_home_matches_K5",
            f"{table_alias}.home_team_elo_home_matches_K10, {table_alias}.away_team_elo_home_matches_K10",
            f"{table_alias}.home_team_elo_home_matches_K20, {table_alias}.away_team_elo_home_matches_K20",
            f"{table_alias}.home_team_elo_home_matches_K30, {table_alias}.away_team_elo_home_matches_K30",
            f"{table_alias}.home_team_elo_home_matches_K40, {table_alias}.away_team_elo_home_matches_K40",
            f"{table_alias}.home_team_elo_home_matches_K80, {table_alias}.away_team_elo_home_matches_K80",
            "",
            f"{table_alias}.home_team_elo_away_matches_K5, {table_alias}.away_team_elo_away_matches_K5",
            f"{table_alias}.home_team_elo_away_matches_K10, {table_alias}.away_team_elo_away_matches_K10",
            f"{table_alias}.home_team_elo_away_matches_K20, {table_alias}.away_team_elo_away_matches_K20",
            f"{table_alias}.home_team_elo_away_matches_K30, {table_alias}.away_team_elo_away_matches_K30",
            f"{table_alias}.home_team_elo_away_matches_K40, {table_alias}.away_team_elo_away_matches_K40",
            f"{table_alias}.home_team_elo_away_matches_K80, {table_alias}.away_team_elo_away_matches_K80",
            "",
            "-- DOMESTIC COMPETITION ELO RATINGS",
            f"{table_alias}.home_team_elo_domestic_K5, {table_alias}.away_team_elo_domestic_K5",
            f"{table_alias}.home_team_elo_domestic_K10, {table_alias}.away_team_elo_domestic_K10",
            f"{table_alias}.home_team_elo_domestic_K20, {table_alias}.away_team_elo_domestic_K20",
            f"{table_alias}.home_team_elo_domestic_K30, {table_alias}.away_team_elo_domestic_K30",
            f"{table_alias}.home_team_elo_domestic_K40, {table_alias}.away_team_elo_domestic_K40",
            f"{table_alias}.home_team_elo_domestic_K80, {table_alias}.away_team_elo_domestic_K80",
            "",
            "-- INTRA-LEAGUE ELO RATINGS",
            f"{table_alias}.home_team_elo_intraleague_K5, {table_alias}.away_team_elo_intraleague_K5",
            f"{table_alias}.home_team_elo_intraleague_K10, {table_alias}.away_team_elo_intraleague_K10",
            f"{table_alias}.home_team_elo_intraleague_K20, {table_alias}.away_team_elo_intraleague_K20",
            f"{table_alias}.home_team_elo_intraleague_K30, {table_alias}.away_team_elo_intraleague_K30",
            f"{table_alias}.home_team_elo_intraleague_K40, {table_alias}.away_team_elo_intraleague_K40",
            f"{table_alias}.home_team_elo_intraleague_K80, {table_alias}.away_team_elo_intraleague_K80",
            "",
            "-- INTERNATIONAL ELO RATINGS",
            f"{table_alias}.home_team_elo_international_K5, {table_alias}.away_team_elo_international_K5",
            f"{table_alias}.home_team_elo_international_K10, {table_alias}.away_team_elo_international_K10",
            f"{table_alias}.home_team_elo_international_K20, {table_alias}.away_team_elo_international_K20",
            f"{table_alias}.home_team_elo_international_K30, {table_alias}.away_team_elo_international_K30",
            f"{table_alias}.home_team_elo_international_K40, {table_alias}.away_team_elo_international_K40",
            f"{table_alias}.home_team_elo_international_K80, {table_alias}.away_team_elo_international_K80",
            "",
            "-- NATION ELO RATINGS",
            f"{table_alias}.home_team_nation_elo_K5, {table_alias}.away_team_nation_elo_K5",
            f"{table_alias}.home_team_nation_elo_K10, {table_alias}.away_team_nation_elo_K10",
            f"{table_alias}.home_team_nation_elo_K20, {table_alias}.away_team_nation_elo_K20",
            f"{table_alias}.home_team_nation_elo_K30, {table_alias}.away_team_nation_elo_K30",
            f"{table_alias}.home_team_nation_elo_K40, {table_alias}.away_team_nation_elo_K40",
            f"{table_alias}.home_team_nation_elo_K80, {table_alias}.away_team_nation_elo_K80",
            "",
            "-- LEAGUE ELO RATINGS",
            f"{table_alias}.home_team_league_domestic_elo_K5, {table_alias}.away_team_league_domestic_elo_K5",
            f"{table_alias}.home_team_league_domestic_elo_K10, {table_alias}.away_team_league_domestic_elo_K10",
            f"{table_alias}.home_team_league_domestic_elo_K20, {table_alias}.away_team_league_domestic_elo_K20",
            f"{table_alias}.home_team_league_domestic_elo_K30, {table_alias}.away_team_league_domestic_elo_K30",
            f"{table_alias}.home_team_league_domestic_elo_K40, {table_alias}.away_team_league_domestic_elo_K40",
            f"{table_alias}.home_team_league_domestic_elo_K80, {table_alias}.away_team_league_domestic_elo_K80",
            "",
            f"{table_alias}.home_team_league_continental_elo_K5, {table_alias}.away_team_league_continental_elo_K5",
            f"{table_alias}.home_team_league_continental_elo_K10, {table_alias}.away_team_league_continental_elo_K10",
            f"{table_alias}.home_team_league_continental_elo_K20, {table_alias}.away_team_league_continental_elo_K20",
            f"{table_alias}.home_team_league_continental_elo_K30, {table_alias}.away_team_league_continental_elo_K30",
            f"{table_alias}.home_team_league_continental_elo_K40, {table_alias}.away_team_league_continental_elo_K40",
            f"{table_alias}.home_team_league_continental_elo_K80, {table_alias}.away_team_league_continental_elo_K80",
            "",
            "-- ELO PARAMETERS",
            f"{table_alias}.k_draw_parameter",
            f"{table_alias}.eta_home_advantage",
            "",
            "-- TEAM IDs",
            f"{table_alias}.home_team_id",
            f"{table_alias}.away_team_id"
        ])
        
        # Stage of season - INNER JOIN (required)
        if self.stage_table in self.feature_tables:
            select_fields.extend([
                "-- STAGE OF SEASON",
                "ssh.stage_of_season",
            ])
            joins.append(f"INNER JOIN {self.stage_table} ssh ON {table_alias}.match_id = ssh.match_id")
        
        # Match info - INNER JOIN (required)
        if self.match_info_table in self.feature_tables:
            select_fields.extend([
                "-- MATCH INFO",
                "mih.competition_id"
            ])
            joins.append(f"INNER JOIN {self.match_info_table} mih ON {table_alias}.match_id = mih.match_id")
        
        # Conditional formations - LEFT JOIN (optional)
        if (self.feature_requirements.get('formations', False) and 
            self.formation_table in self.feature_tables):
            select_fields.extend([
                "-- FORMATION FEATURES",
                "foh.home_team_formation",
                "foh.away_team_formation"
            ])
            joins.append(f"LEFT JOIN {self.formation_table} foh ON {table_alias}.match_id = foh.match_id")
        
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
        """Engineer additional features based on available columns"""
        self.logger.info("Engineering features dynamically")
        
        # Process draw features
        if 'draw_features' in df.columns:
            # Extract draw features from JSONB
            draw_feature_names = [
                'home_draw_rate_3', 'home_draw_rate_5', 'home_draw_rate_10',
                'away_draw_rate_3', 'away_draw_rate_5', 'away_draw_rate_10',
                'both_draw_rate_3', 'both_draw_rate_5', 'both_draw_rate_10',
                'zero_goals_rate_3', 'zero_goals_rate_5', 'zero_goals_rate_10',
                'home_avg_goal_diff_3', 'home_avg_goal_diff_5', 'home_avg_goal_diff_10',
                'away_avg_goal_diff_3', 'away_avg_goal_diff_5', 'away_avg_goal_diff_10'
            ]
            
            # Convert JSONB to dict and extract features
            for feature in draw_feature_names:
                df[feature] = df['draw_features'].apply(
                    lambda x: float(x.get(feature, 0.0)) if isinstance(x, dict) else 0.0
                )
            
            # Drop original draw_features column
            df = df.drop('draw_features', axis=1)
            df = df.drop(['home_team_form', 'away_team_form'], axis=1)
        
        # Drop columns we don't want to use as features
        columns_to_drop = [
            'competition_name',
            'competition_country'
        ]
        df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
        
        # Handle competition_id as category
        if 'competition_id' in df.columns:
            df['competition_id'] = df['competition_id'].astype('category')
        
        # Handle stage of season as category
        if 'stage_of_season' in df.columns:
            df['stage_of_season'] = df['stage_of_season'].astype('category')
        
        return df
    
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

        #TODO: Make this robust to all formations
        
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