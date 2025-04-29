import random
import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_poisson_deviance, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

class PoissonGoalPredictor:
    def __init__(self, test_size=0.1, dev_size=0.1, random_state=42):
        self.test_size = test_size
        self.dev_size = dev_size
        self.random_state = random_state
        self.home_model = make_pipeline(StandardScaler(), PoissonRegressor())
        self.away_model = make_pipeline(StandardScaler(), PoissonRegressor())
        
    def load_data(self):
        # Load your data here
        df = pd.read_csv('data/processed/elo_features.csv')
        df2 = pd.read_csv('data/processed/form_features.csv')

        merged_df = df.merge(df2, on=['match_id'])

        X = merged_df.drop(columns=['match_id', 'home_team_id', 'away_team_id', 'k_draw_parameter', 'eta_home_advantage', 'home_team_score', 'away_team_score'])
        y_home = merged_df['home_team_score']
        y_away = merged_df['away_team_score']

        #remove first 1000 rows
        X = X.iloc[1000:]
        y_home = y_home.iloc[1000:]
        y_away = y_away.iloc[1000:]

        return X, y_home, y_away
    
    def split_data(self, X, y_home, y_away):
        # First split: train+dev vs test
        X_temp, X_test, yh_temp, yh_test, ya_temp, ya_test = train_test_split(
            X, y_home, y_away, 
            test_size=self.test_size,
            random_state=self.random_state
        )
        
        # Second split: train vs dev
        X_train, X_dev, yh_train, yh_dev, ya_train, ya_dev = train_test_split(
            X_temp, yh_temp, ya_temp,
            test_size=self.dev_size/(1-self.test_size),
            random_state=self.random_state
        )
        
        return (X_train, yh_train, ya_train), (X_dev, yh_dev, ya_dev), (X_test, yh_test, ya_test)
    
    def train(self, X_train, yh_train, ya_train):
        self.home_model.fit(X_train, yh_train)
        self.away_model.fit(X_train, ya_train)
        
    def predict(self, X):
        home_preds = self.home_model.predict(X)
        away_preds = self.away_model.predict(X)
        return np.round(home_preds).astype(int), np.round(away_preds).astype(int)
    
    def classify_result(self, X, draw_threshold=0.05):
        """Predict match results with custom draw threshold"""
        home_preds = self.home_model.predict(X)
        away_preds = self.away_model.predict(X)
        
        # Calculate goal difference
        diff = np.abs(home_preds - away_preds)
        
        # Classify results
        results = np.where(diff < draw_threshold, 'draw',
                          np.where(home_preds > away_preds, 'home_win', 'away_win'))
        return results
    
    def evaluate(self, X, yh_true, ya_true, set_name):
        #rounded predictions
        home_preds, away_preds = self.predict(X)

        # Accuracy
        results_true = self._get_results(yh_true, ya_true)
        results_pred = self.classify_result(X, draw_threshold=0.1)
        accuracy = np.mean(results_true == results_pred)
        
        print(f"\n{set_name} Evaluation:")
        print(f"Accuracy: {accuracy:.2%}")
        
        # Show predictions
        self._show_predictions(X, home_preds, away_preds, yh_true, ya_true)
        
        # Confusion matrix
        labels = ['home_win', 'draw', 'away_win']
        cm = confusion_matrix(results_true, results_pred, labels=labels)
        
        print("\nConfusion Matrix:")
        cm_df = pd.DataFrame(cm, index=pd.MultiIndex.from_tuples([('Actual', l) for l in labels]),
                            columns=pd.MultiIndex.from_tuples([('Predicted', l) for l in labels]))
        print(cm_df)
        
        # Normalized matrix
        cm_norm = cm / cm.sum(axis=1, keepdims=True)
        print("\nNormalized Confusion Matrix (Row %):")
        print(pd.DataFrame(cm_norm, index=labels, columns=labels).round(2))
        
    def _get_results(self, home_scores, away_scores):
        return np.where(home_scores > away_scores, 'home_win',
                       np.where(away_scores > home_scores, 'away_win', 'draw'))
    
    def _show_predictions(self, X, home_preds, away_preds, yh_true, ya_true):
        # Get raw predictions
        home_raw = self.home_model.predict(X)
        away_raw = self.away_model.predict(X)
        
        # Create comparison DataFrame
        results = pd.DataFrame({
            'Home Pred Raw': home_raw.round(2),
            'Away Pred Raw': away_raw.round(2),
            'Home Pred Rounded': home_preds,
            'Away Pred Rounded': away_preds,
            'Home Actual': yh_true,
            'Away Actual': ya_true
        })
        
        # Add result comparison
        results['Pred Result'] = self._get_results(results['Home Pred Rounded'], 
                                                  results['Away Pred Rounded'])
        results['Actual Result'] = self._get_results(results['Home Actual'],
                                                    results['Away Actual'])
        
        print("\nPredictions vs Actuals (Dev Set):")
        print(results.sample(30, random_state=self.random_state))
        
    def run(self):
        X, yh, ya = self.load_data()
        (X_train, yh_train, ya_train), (X_dev, yh_dev, ya_dev), (X_test, yh_test, ya_test) = self.split_data(X, yh, ya)
        
        self.train(X_train, yh_train, ya_train)
        
        print("=== Training Set ===")
        print("Length of X_train: ", len(X_train))
        print(len(X_train))
        self.evaluate(X_train, yh_train, ya_train, "Training")
        
        print("\n=== Development Set ===")
        print("Length of X_dev: ", len(X_dev))
        print(len(X_dev))
        self.evaluate(X_dev, yh_dev, ya_dev, "Development")
        
        # print("\n=== Test Set ===")
        # self.evaluate(X_test, yh_test, ya_test, "Test")

if __name__ == "__main__":
    model = PoissonGoalPredictor()
    model.run()