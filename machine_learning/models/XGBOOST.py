import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import OrdinalEncoder
from imblearn.over_sampling import SMOTE
from helpers.machine_learning.load_data import prepare_data

def xgboost_model(remove_draws=False, training_data_filter=None, test_year=None, test_competition_id=None):

    y_dev = None
    y_test = None
    X_dev = None
    
    if test_competition_id and test_year:
        X_train, y_train, X_test, y_test = prepare_data(remove_draws, training_data_filter, test_year, test_competition_id)
        print(X_test.head())
        print(y_test.head())
        X_train, metadata_train = prepare_data_for_inference(X_train)
        X_test, metadata_test = prepare_data_for_inference(X_test)
    else:
        # This is one instance of a k-fold cross validation.
        # We need to perform the following steps for each fold
        # For 1 to k, prepare the data 
        X_train, y_train, X_dev, y_dev, X_test, y_test = prepare_data(remove_draws, training_data_filter)
        X_train, metadata_train = prepare_data_for_inference(X_train)
        X_dev, metadata_dev = prepare_data_for_inference(X_dev)
        X_test, metadata_test = prepare_data_for_inference(X_test)


    desired_order = [['home_win', 'draw', 'away_win']]  # Note double list
    encoder = OrdinalEncoder(categories=desired_order)
    y_train_encoded = encoder.fit_transform(y_train.to_numpy().reshape(-1, 1)).flatten().astype(int)
    if y_dev is not None:
        y_dev_encoded = encoder.transform(y_dev.to_numpy().reshape(-1, 1)).flatten().astype(int)
    if y_test is not None:
        y_test_encoded = encoder.transform(y_test.to_numpy().reshape(-1, 1)).flatten().astype(int)


    if X_dev is not None:
        print(f"Train: {len(X_train)}, Dev: {len(X_dev)}, Test: {len(X_test)}")
    else:
        print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    print("Encoded values:")
    print(np.unique(y_train_encoded, return_counts=True))
    print("Category mapping:", encoder.categories_)
    
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

    #     # SMOTE
    # smote = SMOTE(random_state=42)
    # X_train, y_train = smote.fit_resample(X_train, y_train_encoded)

    # Pass weights during training
    xgb_classifier.fit(
    X_train, y_train_encoded,
    sample_weight=sample_weights,
    eval_set=[(X_test, y_test_encoded)],
    verbose=True
)
    
    if test_competition_id and test_year and metadata_test is not None:
        #save predictions
        predictions = xgb_classifier.predict(X_test)
        probabilities = xgb_classifier.predict_proba(X_test)

        #inverse transform
        y_test_2d = y_test_encoded.reshape(-1, 1)
        y_test_labels = encoder.inverse_transform(y_test_2d).flatten()

        # Option 1: Start with metadata copy and add new columns
        results = metadata_test.copy()
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
    
    else:
        y_dev_pred = xgb_classifier.predict(X_dev)
        y_train_pred = xgb_classifier.predict(X_train)

        # Inverse transform
        y_dev_2d = y_dev_encoded.reshape(-1, 1)
        y_train_2d = y_train_encoded.reshape(-1, 1)
        # Inverse transform
        y_dev_labels = encoder.inverse_transform(y_dev_2d).flatten()
        y_train_labels = encoder.inverse_transform(y_train_2d).flatten()

        # Similarly for predictions
        y_dev_pred_2d = y_dev_pred.reshape(-1, 1)  # y_pred is numpy array
        y_dev_pred_labels = encoder.inverse_transform(y_dev_pred_2d).flatten()

        y_train_pred_2d = y_train_pred.reshape(-1, 1)  # y_pred is numpy array
        y_train_pred_labels = encoder.inverse_transform(y_train_pred_2d).flatten()

        # Update all metrics to use original labels
        train_overall_accuracy = accuracy_score(y_train_labels, y_train_pred_labels)
        dev_overall_accuracy = accuracy_score(y_dev_labels, y_dev_pred_labels)

        #Print both train and dev accuracy and both classification reports and confusion matrices

        print(f"\nDev Overall Accuracy: {dev_overall_accuracy:.3f}")
        print(f"\nTrain Overall Accuracy: {train_overall_accuracy:.3f}")

        print("\nDev Classification Report:")
        print(classification_report(y_dev_labels, y_dev_pred_labels))

        print("\nTrain Classification Report:")
        print(classification_report(y_train_labels, y_train_pred_labels))
    
        cm_dev = confusion_matrix(y_dev_labels, y_dev_pred_labels, labels=encoder.categories_[0])
        print("\nDev Confusion Matrix:\n")
        print(pd.DataFrame(cm_dev, 
                      index=encoder.categories_[0], 
                      columns=encoder.categories_[0]))

        cm_train = confusion_matrix(y_train_labels, y_train_pred_labels, labels=encoder.categories_[0])
        print("\nTrain Confusion Matrix:")
        print(pd.DataFrame(cm_train, 
                      index=encoder.categories_[0], 
                      columns=encoder.categories_[0]))

    
        # Additional metrics    
        print("\nDev Additional Metrics:")
        print(f"- Weighted Avg F1: {classification_report(y_dev_labels, y_dev_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
        print(f"- Macro Avg Precision: {classification_report(y_dev_labels, y_dev_pred_labels, output_dict=True)['macro avg']['precision']:.2f}")

        print("\nTrain Additional Metrics:")
        print(f"- Weighted Avg F1: {classification_report(y_train_labels, y_train_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
        print(f"- Macro Avg Precision: {classification_report(y_train_labels, y_train_pred_labels, output_dict=True)['macro avg']['precision']:.2f}") 

def prepare_data_for_inference(df):
    # Store metadata columns you want to keep
    metadata = df[['match_id', 'start_time', 'home_team_name', 'away_team_name', 'competition_name', 'competition_season_name', 'competition_country', 'home_team_score', 'away_team_score']]
    
    # Create feature matrix without these columns
    X = df.drop(columns=['match_id', 'home_team_id','away_team_id', 'home_team_name', 'away_team_name', 'k_draw_parameter', 'eta_home_advantage','start_time','competition_season_name', 
                'competition_name','competition_country', 'home_team_score', 'away_team_score'])
    
    return X, metadata

if __name__ == "__main__":
    #Need to perform cross validation to ensure the accuracies are stable
    #Evaluate the model on different sets of dev data
    xgboost_model(remove_draws=False, training_data_filter=[61,140,39,3])