import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from imblearn.over_sampling import SMOTE



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

def xgboost_draw_model():
    X, y = prepare_data(remove_draws=False)
    #combine home win and away win into one class called not_draw
    y = np.where(y == 'home_win', 'not_draw', np.where(y == 'away_win', 'not_draw', 'draw'))

    desired_order = [['not_draw', 'draw']]  # Note double list
    encoder = OrdinalEncoder(categories=desired_order)
    y_encoded = encoder.fit_transform(y.reshape(-1, 1)).flatten().astype(int)

    # Split encoded data
    X_train, X_temp, y_train, y_temp = train_test_split(X, y_encoded, test_size=0.2)
    X_dev, X_test, y_dev, y_test = train_test_split(X_temp, y_temp, test_size=0.5)

    # #SMOTE
    # smote = SMOTE(random_state=42)
    # X_train, y_train = smote.fit_resample(X_train, y_train)

    #print how many of each class in training now
    print(np.unique(y_train, return_counts=True))
    print(f"Train: {len(X_train)}, Dev: {len(X_dev)}, Test: {len(X_test)}")
    print("Encoded values:")
    print(np.unique(y, return_counts=True))
    
    class_weights = {
    'not_draw': 1,  # 0
    'draw': 3,       # 1
    }
    sample_weights = np.array([class_weights[encoder.categories_[0][y]] for y in y_train])

    xgb_classifier = xgb.XGBClassifier(
        n_estimators=100,
        objective='binary:logistic',
        tree_method='hist',
        eta=0.1,
        max_depth=3,
        enable_categorical=True
    )
    # Pass weights during training
    xgb_classifier.fit(
    X_train, y_train,
    sample_weight=sample_weights,
    eval_set=[(X_test, y_test)],
    verbose=True
)

    #evaluate on dev
    y_dev_pred = xgb_classifier.predict(X_dev)
    y_train_pred = xgb_classifier.predict(X_train)
    
    # Convert y_dev (pandas Series) to 2D numpy array
    y_dev_2d = y_dev.reshape(-1, 1)
    y_train_2d = y_train.reshape(-1, 1)
    # Inverse transform
    y_dev_labels = encoder.inverse_transform(y_dev_2d).flatten()
    y_train_labels = encoder.inverse_transform(y_train_2d).flatten()

    # Similarly for predictions
    y_dev_pred_2d = y_dev_pred.reshape(-1, 1)  # y_pred is numpy array
    y_dev_pred_labels = encoder.inverse_transform(y_dev_pred_2d).flatten()

    y_train_pred_2d = y_train_pred.reshape(-1, 1)  # y_pred is numpy array
    y_train_pred_labels = encoder.inverse_transform(y_train_pred_2d).flatten()
    
    # Update all metrics to use original labels
    train_overall_accuracy = accuracy_score(y_train, y_train_pred)
    dev_overall_accuracy = accuracy_score(y_dev_labels, y_dev_pred_labels)

    #Print both train and dev accuracy and both classification reports and confusion matrices

    print(f"\nDev Overall Accuracy: {dev_overall_accuracy:.3f}")
    print(f"\nTrain Overall Accuracy: {train_overall_accuracy:.3f}")

    print("\nDev Classification Report:")
    print(classification_report(y_dev_labels, y_dev_pred_labels))

    print("\nTrain Classification Report:")
    print(classification_report(y_train_labels, y_train_pred_labels))
    
    cm_dev = confusion_matrix(y_dev_labels, y_dev_pred_labels, labels=encoder.categories_[0])
    print("\nDev Confusion Matrix:")
    print(pd.DataFrame(cm_dev, 
                      index=encoder.categories_[0], 
                      columns=encoder.categories_[0]))

    cm_train = confusion_matrix(y_train_labels, y_train_pred_labels, labels=encoder.categories_[0])
    print("\nTrain Confusion Matrix:")
    print(pd.DataFrame(cm_train, 
                      index=encoder.categories_[0], 
                      columns=encoder.categories_[0]))
    
    # Optional: Visualize confusion matrix
    plt.figure(figsize=(10,7))
    sns.heatmap(cm_dev, annot=True, fmt='d', cmap='Blues', 
               xticklabels=encoder.categories_[0], 
               yticklabels=encoder.categories_[0])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()

    plt.figure(figsize=(10,7))
    sns.heatmap(cm_train, annot=True, fmt='d', cmap='Blues', 
               xticklabels=encoder.categories_[0], 
               yticklabels=encoder.categories_[0])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()

def xgboost_model():
    X, y = prepare_data()
    desired_order = [['home_win', 'draw', 'away_win']]  # Note double list
    encoder = OrdinalEncoder(categories=desired_order)
    y_encoded = encoder.fit_transform(y.to_numpy().reshape(-1, 1)).flatten().astype(int)

    # Split encoded data
    X_train, X_temp, y_train, y_temp = train_test_split(X, y_encoded, test_size=0.2)
    X_dev, X_test, y_dev, y_test = train_test_split(X_temp, y_temp, test_size=0.5)

    #print how many of each class in training now
    print(np.unique(y_train, return_counts=True))
    

    print(f"Train: {len(X_train)}, Dev: {len(X_dev)}, Test: {len(X_test)}")
    print("Encoded values:")
    print(np.unique(y_encoded, return_counts=True))
    print("Category mapping:", encoder.categories_)
    
    class_weights = {
    'home_win': 1,  # 0
    'draw': 1,       # 1
    'away_win': 1    # 2
    }
    sample_weights = np.array([class_weights[encoder.categories_[0][y]] for y in y_train])

    xgb_classifier = xgb.XGBClassifier(
        n_estimators=100,
        objective='multi:softprob',
        tree_method='hist',
        eta=0.1,
        max_depth=3,
        enable_categorical=True
    )
    # Pass weights during training
    xgb_classifier.fit(
    X_train, y_train,
    sample_weight=sample_weights,
    eval_set=[(X_test, y_test)],
    verbose=True
)

    y_dev_pred = xgb_classifier.predict(X_dev)
    y_train_pred = xgb_classifier.predict(X_train)
    
    # Convert y_dev (pandas Series) to 2D numpy array
    y_dev_2d = y_dev.reshape(-1, 1)
    y_train_2d = y_train.reshape(-1, 1)
    # Inverse transform
    y_dev_labels = encoder.inverse_transform(y_dev_2d).flatten()
    y_train_labels = encoder.inverse_transform(y_train_2d).flatten()

    # Similarly for predictions
    y_dev_pred_2d = y_dev_pred.reshape(-1, 1)  # y_pred is numpy array
    y_dev_pred_labels = encoder.inverse_transform(y_dev_pred_2d).flatten()

    y_train_pred_2d = y_train_pred.reshape(-1, 1)  # y_pred is numpy array
    y_train_pred_labels = encoder.inverse_transform(y_train_pred_2d).flatten()
    
    # Update all metrics to use original labels
    train_overall_accuracy = accuracy_score(y_train, y_train_pred)
    dev_overall_accuracy = accuracy_score(y_dev_labels, y_dev_pred_labels)

    #Print both train and dev accuracy and both classification reports and confusion matrices

    print(f"\nDev Overall Accuracy: {dev_overall_accuracy:.3f}")
    print(f"\nTrain Overall Accuracy: {train_overall_accuracy:.3f}")

    print("\nDev Classification Report:")
    print(classification_report(y_dev_labels, y_dev_pred_labels))

    print("\nTrain Classification Report:")
    print(classification_report(y_train_labels, y_train_pred_labels))
    
    cm_dev = confusion_matrix(y_dev_labels, y_dev_pred_labels, labels=encoder.categories_[0])
    print("\nDev Confusion Matrix:")
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

    

if __name__ == "__main__":
    # X, y = prepare_data()
    #print all columns
    #save to text file
    # with open('columns.txt', 'w') as f:
    #     for column in X.columns:
    #         f.write(column + '\n')
    # columns_to_analyse = ['home_draws_in_last_5', 'away_draws_in_last_5', 'home_team_elo_K30', 'away_team_elo_K30', 'home_draws_in_last_10', 'away_draws_in_last_10', ]
    # #drop all but columns_to_analyse
    # X = X[columns_to_analyse]
    # #change y to be either draw or not draw
    # #so home_win= 0 ,away win=0, draw=1
    # #basically if its a draw mark it as 1 otherwise 0
    # #drop the first 1000
    # X = X.iloc[1000:]
    # y = y.iloc[1000:]
    # # Convert y to binary 'draw' vs 'not_draw'
    # y_binary = np.where(y == 'draw', 'draw', 'not_draw')

    # # Create DataFrame for plotting
    # plot_df = X.copy()
    # plot_df['result'] = y_binary

    # # Generate pairplot
    # sns.pairplot(plot_df, hue='result', palette={'draw': 'red', 'not_draw': 'blue'})
    # plt.show()
    xgboost_model()