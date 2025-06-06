from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging


class BaseFeatureLoader(ABC):
    """
    Abstract base class for feature loaders
    Handles database connections and provides common functionality
    """
    
    def __init__(self, conn, config: Dict[str, Any]):
        self.conn = conn
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Feature configuration
        self.feature_tables = self.config.get('feature_tables', [])
        self.target_column = self.config.get('target_column', None)
        self.match_id_column = self.config.get('match_id_column', 'match_id')
        
    @abstractmethod
    def get_required_tables(self) -> List[str]:
        """
        Return list of required database tables for this feature set
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def load_features(self, where_clause: Optional[str] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load and prepare features for the model
        Must be implemented by subclasses
        
        Args:
            where_clause: Optional SQL WHERE clause to filter data
            limit: Optional limit on number of records
            
        Returns:
            DataFrame with features and match_id as index
        """
        pass
    
    @abstractmethod
    def load_targets(self, match_ids: Optional[List[int]] = None) -> pd.Series:
        """
        Load target variable for the model
        Must be implemented by subclasses
        
        Args:
            match_ids: Optional list of match IDs to filter
            
        Returns:
            Series with targets and match_id as index
        """
        pass
    
    def load_data(self, where_clause: Optional[str] = None, 
                  limit: Optional[int] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load both features and targets, ensuring they're aligned
        
        Args:
            where_clause: Optional SQL WHERE clause to filter data
            limit: Optional limit on number of records
            
        Returns:
            Tuple of (features_df, targets_series) with aligned indices
        """
        self.logger.info("Loading features and targets")
        
        # Load features
        features = self.load_features(where_clause=where_clause, limit=limit)
        self.logger.info(f"Loaded {len(features)} feature records with {len(features.columns)} columns")
        
        # Load targets for the same match IDs
        match_ids = features.index.tolist()
        targets = self.load_targets(match_ids=match_ids)
        self.logger.info(f"Loaded {len(targets)} target records")
        
        # Align features and targets
        common_indices = features.index.intersection(targets.index)
        features_aligned = features.loc[common_indices]
        targets_aligned = targets.loc[common_indices]
        
        self.logger.info(f"Final dataset: {len(features_aligned)} samples with {len(features_aligned.columns)} features")
        
        return features_aligned, targets_aligned
    
    def check_data_quality(self, features: pd.DataFrame, targets: pd.Series) -> Dict[str, Any]:
        """
        Check data quality and return summary statistics
        
        Args:
            features: Feature DataFrame
            targets: Target Series
            
        Returns:
            Dictionary with data quality metrics
        """
        quality_report = {
            'total_samples': len(features),
            'total_features': len(features.columns),
            'missing_values': features.isnull().sum().to_dict(),
            'target_distribution': targets.value_counts().to_dict() if targets.dtype == 'object' else {
                'mean': targets.mean(),
                'std': targets.std(),
                'min': targets.min(),
                'max': targets.max()
            },
            'feature_types': features.dtypes.value_counts().to_dict(),
            'duplicate_rows': features.duplicated().sum(),
            'infinite_values': {}
        }
        
        # Check for infinite values in numeric columns
        numeric_cols = features.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            inf_count = (features[col] == float('inf')).sum() + (features[col] == float('-inf')).sum()
            if inf_count > 0:
                quality_report['infinite_values'][col] = inf_count
        
        return quality_report
    
    def clean_data(self, features: pd.DataFrame, targets: pd.Series, 
                   drop_missing_threshold: float = 0.5) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Clean data by handling missing values, duplicates, etc.
        
        Args:
            features: Feature DataFrame
            targets: Target Series
            drop_missing_threshold: Drop columns with more than this fraction of missing values
            
        Returns:
            Cleaned features and targets
        """
        self.logger.info("Cleaning data")
        initial_shape = features.shape
        
        # Drop columns with too many missing values
        missing_fraction = features.isnull().mean()
        cols_to_drop = missing_fraction[missing_fraction > drop_missing_threshold].index
        if len(cols_to_drop) > 0:
            self.logger.warning(f"Dropping {len(cols_to_drop)} columns with >{drop_missing_threshold*100}% missing values")
            features = features.drop(columns=cols_to_drop)
        
        # Drop rows where target is missing
        target_not_null = targets.notna()
        features = features[target_not_null]
        targets = targets[target_not_null]
        
        # Handle infinite values in numeric columns
        numeric_cols = features.select_dtypes(include=['number']).columns
        features[numeric_cols] = features[numeric_cols].replace([float('inf'), float('-inf')], pd.NA)
        
        # Fill remaining missing values
        for col in features.columns:
            if features[col].dtype in ['int64', 'float64']:
                # Fill numeric with median
                features[col] = features[col].fillna(features[col].median())
            else:
                # Fill categorical with mode
                mode_val = features[col].mode()
                fill_val = mode_val[0] if len(mode_val) > 0 else 'unknown'
                features[col] = features[col].fillna(fill_val)
        
        # Remove duplicate rows
        before_dedup = len(features)
        features = features.drop_duplicates()
        targets = targets.loc[features.index]
        after_dedup = len(features)
        
        if before_dedup != after_dedup:
            self.logger.info(f"Removed {before_dedup - after_dedup} duplicate rows")
        
        self.logger.info(f"Data cleaning complete: {initial_shape} -> {features.shape}")
        return features, targets
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            Query results as DataFrame
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute(query, params)
            results = cursor.fetchall()
            if results:
                return pd.DataFrame(results)
            else:
                return pd.DataFrame()
        finally:
            cursor.close()
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a given table
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """
        result = self.execute_query(query, (table_name,))
        return result['column_name'].tolist() if not result.empty else []
    
    def validate_required_tables(self) -> bool:
        """
        Validate that all required tables exist in the database
        
        Returns:
            True if all tables exist, False otherwise
        """
        required_tables = self.get_required_tables()
        
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
            AND table_name = ANY(%s)
        """
        existing_tables = self.execute_query(query, (required_tables,))
        existing_table_names = existing_tables['table_name'].tolist() if not existing_tables.empty else []
        
        missing_tables = set(required_tables) - set(existing_table_names)
        
        if missing_tables:
            self.logger.error(f"Missing required tables: {missing_tables}")
            return False
        
        self.logger.info("All required tables found")
        return True 