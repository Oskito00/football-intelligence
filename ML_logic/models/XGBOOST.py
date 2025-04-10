import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder


def load_csv_data(file_path):
    """Load CSV data into a pandas DataFrame.
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        pd.DataFrame: Loaded data or None if error occurs
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded data from {file_path}")
        # print(f"Shape: {df.shape}")
        # print("Columns:", df.columns.tolist())
        return df
    except Exception as e:
        print(f"Error loading {file_path}: {str(e)}")
        return None

def xgboost_model():
    df = load_csv_data('Data/processed/elo_features.csv')

    # FIRST create the result column
    df['result'] = np.where(df['home_team_score'] > df['away_team_score'], 'home_win', 
                           np.where(df['home_team_score'] < df['away_team_score'], 'away_win', 'draw'))
    
    # THEN drop it from features
    X = df.drop(columns=['match_id', 'home_team_id', 'away_team_id', 
                        'home_team_score', 'away_team_score', 'k_draw_parameter', 'eta_home_advantage', 'result'])
    
    
    y = df['result']
    
    # Add label encoding
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Update train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=39
    )


    xgb_classifier = xgb.XGBClassifier(
        n_estimators=100,
        objective='multi:softprob',
        tree_method='hist',
        eta=0.1,
        max_depth=3,
        enable_categorical=True
    )
    xgb_classifier.fit(X_train, y_train)

    y_pred = xgb_classifier.predict(X_test)
    
    # Convert back to original labels for reporting
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)
    
    # Update all metrics to use original labels
    overall_accuracy = accuracy_score(y_test_labels, y_pred_labels)
    print(f"\nOverall Accuracy: {overall_accuracy:.2f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test_labels, y_pred_labels))
    
    cm = confusion_matrix(y_test_labels, y_pred_labels, labels=le.classes_)
    print("\nConfusion Matrix:")
    print(pd.DataFrame(cm, 
                      index=le.classes_, 
                      columns=le.classes_))
    
    # Additional metrics
    print("\nAdditional Metrics:")
    print(f"- Weighted Avg F1: {classification_report(y_test_labels, y_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
    print(f"- Macro Avg Precision: {classification_report(y_test_labels, y_pred_labels, output_dict=True)['macro avg']['precision']:.2f}")

    # Optional: Visualize confusion matrix
    # plt.figure(figsize=(10,7))
    # sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
    #            xticklabels=le.classes_, 
    #            yticklabels=le.classes_)
    # plt.xlabel('Predicted')
    # plt.ylabel('True')
    # plt.title('Confusion Matrix')
    # plt.show()

if __name__ == "__main__":
    xgboost_model()