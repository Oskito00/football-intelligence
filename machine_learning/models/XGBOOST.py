from tqdm import tqdm
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, train_test_split
import xgboost as xgb
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.preprocessing import OrdinalEncoder
from helpers.machine_learning.load_data import prepare_data

def xgboost_model(num_folds=10, remove_draws=False, training_data_filter=None, test_year=None, test_competition_id=None):
    y_test = None
    
    if test_competition_id and test_year:
        X_train, y_train, X_test, y_test = prepare_data(remove_draws, training_data_filter, test_year, test_competition_id)
        X_train, X_metadata_train = prepare_data_for_inference(X_train)
        X_test, X_metadata_test = prepare_data_for_inference(X_test)
    else:
        X, y = prepare_data(remove_draws, training_data_filter)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42) #Always have the same test set
        
        X_train, X_metadata_train = prepare_data_for_inference(X_train)
        X_test, X_metadata_test = prepare_data_for_inference(X_test)
    
    desired_order = [['home_win', 'draw', 'away_win']]  # Note double list
    encoder = OrdinalEncoder(categories=desired_order)
    y_train_encoded = encoder.fit_transform(y_train.to_numpy().reshape(-1, 1)).flatten().astype(int)
    if y_test is not None:
        y_test_encoded = encoder.transform(y_test.to_numpy().reshape(-1, 1)).flatten().astype(int)
    
    class_weights = {
    'home_win': 1,  # 0
    'draw': 1,       # 1
    'away_win': 1    # 2
    }
    sample_weights = np.array([class_weights[encoder.categories_[0][y]] for y in y_train_encoded])

    xgb_classifier = xgb.XGBClassifier(
        n_estimators=100,
        objective='multi:softprob',
        tree_method='hist',
        eta=0.1,
        max_depth=3,
        enable_categorical=True
    )

    cross_val_results = cross_val_score(xgb_classifier, X_train, y_train_encoded, cv=num_folds)
    print(f"Cross-validation results: {cross_val_results}")

    print("Cross-Validation Results (Accuracy):")
    for i, result in enumerate(cross_val_results, 1):
        print(f"  Fold {i}: {result * 100:.2f}%")
    print(f'Mean Accuracy: {cross_val_results.mean()* 100:.2f}%')

    print("Training model...")

     # Modified training code with progress bar
    # Train the model without tqdm
    xgb_classifier.fit(
    X_train, y_train_encoded,
    sample_weight=sample_weights,
    eval_set=[(X_test, y_test_encoded)],
    verbose=False  # You can set this to True or a number if you want minimal progress info
    )

    # Save the trained model
    model_path = "machine_learning/saved_model_params/XGBOOST/xgboost_model_match_outcome.joblib"
    xgb_classifier.save_model(model_path)
    print(f"Model saved to {model_path}")

    
    if test_competition_id and test_year and X_metadata_test is not None:
        #save predictions
        predictions = xgb_classifier.predict(X_test)
        probabilities = xgb_classifier.predict_proba(X_test)

        #inverse transform
        y_test_2d = y_test_encoded.reshape(-1, 1)
        y_test_labels = encoder.inverse_transform(y_test_2d).flatten()

        # Option 1: Start with metadata copy and add new columns
        results = X_metadata_test.copy()
        results['predicted_result'] = predictions

        # Add probability columns (adjust indices based on your class ordering)
        results['home_win_prob'] = probabilities[:, 0]  
        results['draw_prob'] = probabilities[:, 1]
        results['away_win_prob'] = probabilities[:, 2]

        #add the original labels
        results['original_result'] = y_test_labels

        print(f"Predictions combined with metadata, total rows: {len(results)}")

        #save to csv
        results.to_csv(f"machine_learning/predictions/XGBOOST/predictions/predictions_{test_competition_id}_{test_year}.csv", index=False)
        #print accuracy and confusion matrix
        print(f"Accuracy: {accuracy_score(y_test_encoded, predictions)}")
        print(f"Confusion Matrix:\n {confusion_matrix(y_test_encoded, predictions)}")
        return results
    
def prepare_data_for_inference(df):
    # Store metadata columns you want to keep
    metadata = df[['match_id', 'start_time', 'home_team_name', 'away_team_name', 'competition_name', 'competition_season_name', 'competition_country', 'home_team_score', 'away_team_score']]
    
    # Create feature matrix without these columns
    X = df.drop(columns=['match_id', 'home_team_id','away_team_id', 'home_team_name', 'away_team_name', 'k_draw_parameter', 'eta_home_advantage','start_time','competition_season_name', 
                'competition_name','competition_country', 'home_team_score', 'away_team_score'])
    
    return X, metadata

if __name__ == "__main__":
    xgboost_model(remove_draws=False, num_folds=10)
    # xgboost_model(remove_draws=False, num_folds=10, training_data_filter=None, test_year=2021, test_competition_id=61)