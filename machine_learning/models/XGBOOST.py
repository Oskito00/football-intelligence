import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder


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

def prepare_data(remove_draws=False):
    df = load_csv_data('Data/processed/elo_features.csv')
    form_df = load_csv_data('Data/processed/form_features.csv')

    #add form_df columns to df
    df = df.merge(form_df, on=['match_id'])

    # FIRST create the result column
    df['result'] = np.where(df['home_team_score'] > df['away_team_score'], 'home_win', 
                           np.where(df['home_team_score'] < df['away_team_score'], 'away_win', 'draw'))
    
    if remove_draws:
        df = df[df['result'] != 'draw']

    # THEN drop it from features
    X = df.drop(columns=['match_id', 'home_team_id', 'away_team_id', 
                        'home_team_score', 'away_team_score', 'k_draw_parameter', 'eta_home_advantage', 'result'])
    
    #length of the columns of X
    print(len(X.columns))
    
    y = df['result']


    return X, y

def sns_pairplot(X, y, target_name='result'):
    """
    Generate pairplot with target as hue.
    
    Args:
        X: DataFrame or array-like of features
        y: Series or array-like of target values
        target_name: Name for target column (default 'result')
    """
    # Convert to DataFrames if not already
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)
    if not isinstance(y, pd.Series):
        y = pd.Series(y, name=target_name)
    
    # Combine features and target
    data = X.join(y)
    
    # Generate pairplot
    sns.pairplot(data, hue=target_name)
    plt.show()

def xgboost_model():
    X, y = prepare_data()
    #drop first 1000
    X = X.iloc[1000:]
    y = y.iloc[1000:]
    # Add label encoding
    # Define and validate class order
    desired_order = [['home_win', 'draw', 'away_win']]  # Note double list
    
    # Initialize encoder with specified categories
    encoder = OrdinalEncoder(categories=desired_order)
    
    # Reshape y to 2D array required by OrdinalEncoder
    y_reshaped = y.values.reshape(-1, 1)
    y_encoded = encoder.fit_transform(y_reshaped).flatten().astype(int)
    
    # Verification
    print("Encoded values:")
    print(np.unique(y_encoded, return_counts=True))
    print("Category mapping:", encoder.categories_)
    
    # Update train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=165
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
    y_test_labels = encoder.inverse_transform(y_test.reshape(-1, 1)).flatten()
    y_pred_labels = encoder.inverse_transform(y_pred.reshape(-1, 1)).flatten()
    
    # Update all metrics to use original labels
    overall_accuracy = accuracy_score(y_test_labels, y_pred_labels)
    print(f"\nOverall Accuracy: {overall_accuracy:.3f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test_labels, y_pred_labels))
    
    cm = confusion_matrix(y_test_labels, y_pred_labels, labels=encoder.categories_[0])
    print("\nConfusion Matrix:")
    print(pd.DataFrame(cm, 
                      index=encoder.categories_[0], 
                      columns=encoder.categories_[0]))
    
    # Additional metrics
    print("\nAdditional Metrics:")
    print(f"- Weighted Avg F1: {classification_report(y_test_labels, y_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
    print(f"- Macro Avg Precision: {classification_report(y_test_labels, y_pred_labels, output_dict=True)['macro avg']['precision']:.2f}")

    # Optional: Visualize confusion matrix
    plt.figure(figsize=(10,7))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
               xticklabels=encoder.categories_[0], 
               yticklabels=encoder.categories_[0])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()

if __name__ == "__main__":
    X, y = prepare_data()
    columns_to_analyse = ['home_draws_in_last_5', 'away_draws_in_last_5', 'home_team_elo_K30', 'away_team_elo_K30', 'home_draws_in_last_10', 'away_draws_in_last_10', ]
    #drop all but columns_to_analyse
    X = X[columns_to_analyse]
    #change y to be either draw or not draw
    #so home_win= 0 ,away win=0, draw=1
    #basically if its a draw mark it as 1 otherwise 0
    #drop the first 1000
    X = X.iloc[1000:]
    y = y.iloc[1000:]
    # Convert y to binary 'draw' vs 'not_draw'
    y_binary = np.where(y == 'draw', 'draw', 'not_draw')

    # Create DataFrame for plotting
    plot_df = X.copy()
    plot_df['result'] = y_binary

    # Generate pairplot
    sns.pairplot(plot_df, hue='result', palette={'draw': 'red', 'not_draw': 'blue'})
    plt.show()
    # xgboost_model()