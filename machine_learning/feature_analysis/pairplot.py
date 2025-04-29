import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

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