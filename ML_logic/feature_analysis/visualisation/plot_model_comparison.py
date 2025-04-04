import matplotlib.pyplot as plt
import numpy as np

def plot_model_comparison(accuracies):
    """Plot train/dev accuracies with error bars from cross-validation"""
    model_names = ['Basic', 'Advanced', 'Ensemble']
    x = np.arange(len(model_names))
    width = 0.35
    
    plt.figure(figsize=(12, 6))
    
    # Plot train and dev bars with error bars
    train_means = [acc[0] for acc in accuracies['train']]
    train_stds = [acc[1] for acc in accuracies['train']]
    dev_means = [acc[0] for acc in accuracies['dev']]
    dev_stds = [acc[1] for acc in accuracies['dev']]
    
    plt.bar(x - width/2, train_means, width, yerr=train_stds, 
            label='Train', color='skyblue', capsize=5)
    plt.bar(x + width/2, dev_means, width, yerr=dev_stds, 
            label='Dev', color='lightgreen', capsize=5)
    
    plt.ylabel('Accuracy')
    plt.title('Model Performance Comparison (Cross-Validated)')
    plt.xticks(x, model_names)
    plt.legend()
    
    # Add value labels
    for i in range(len(model_names)):
        plt.text(i - width/2, train_means[i], 
                f'{train_means[i]:.3f}\n±{train_stds[i]:.3f}', 
                ha='center', va='bottom')
        plt.text(i + width/2, dev_means[i], 
                f'{dev_means[i]:.3f}\n±{dev_stds[i]:.3f}', 
                ha='center', va='bottom')
    
    plt.tight_layout()
    plt.show()

def plot_classification_metrics(cv_reports, model_names):
    """Plot CV classification metrics with error bars"""
    classes = ['Home Win', 'Draw', 'Away Win']
    metrics = ['precision', 'recall', 'f1-score']
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    x = np.arange(len(metrics))
    width = 0.8 / len(model_names)
    
    for idx, (class_name, ax) in enumerate(zip(classes, axes)):
        for i, ((report, std), model) in enumerate(zip(cv_reports, model_names)):
            # Get scores and errors for current class
            scores = [report[str(idx)][metric] for metric in metrics]
            errors = [std[str(idx)][metric] for metric in metrics]
            
            # Plot bars with error bars
            position = x + (i - len(model_names)/2 + 0.5) * width
            ax.bar(position, scores, width, yerr=errors, 
                  label=model, capsize=5)
            
            # Add value labels
            for j, (score, error) in enumerate(zip(scores, errors)):
                pos = j + (i - len(model_names)/2 + 0.5) * width
                ax.text(pos, score, f'{score:.2f}\n±{error:.2f}', 
                       ha='center', va='bottom', fontsize=8)
        
        ax.set_title(class_name)
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=45)
        ax.set_ylim(0, 1)
        
        if idx == 0:
            ax.legend()
    
    plt.suptitle('Cross-Validated Classification Metrics by Class')
    plt.tight_layout()
    plt.show()