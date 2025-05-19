import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns

from helpers.machine_learning.load_data import prepare_data, prepare_data_for_inference


class FootballNN(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_classes=3, dropout_rate=0.3):
        """
        Neural Network for football match prediction
        
        Args:
            input_size: Number of input features
            hidden_size: Size of hidden layers
            num_classes: Number of output classes (3 for win/draw/loss)
            dropout_rate: Dropout probability for regularization
        """
        super(FootballNN, self).__init__()
        
        # Network architecture
        self.model = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.BatchNorm1d(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_size, hidden_size),
            nn.BatchNorm1d(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_size, hidden_size // 2),
            nn.BatchNorm1d(hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_size // 2, num_classes)
        )
    
    def forward(self, x):
        return self.model(x)


def neural_network_model(remove_draws=False, training_data_filter=None, test_year=None, test_competition_id=None):
    """
    Train and evaluate a neural network model for football match prediction
    
    Args:
        remove_draws: Whether to exclude draws from the dataset
        training_data_filter: List of competition IDs to include in training
        test_year: Year to use for testing
        test_competition_id: Competition ID to use for testing
    
    Returns:
        Trained model and evaluation metrics
    """
    y_dev = None
    y_test = None
    X_dev = None
    

    if test_competition_id and test_year:
        X_train, y_train, X_test, y_test = prepare_data(remove_draws, training_data_filter, test_year, test_competition_id)
        print(f"Training data shape: {X_train.shape}")
        print(f"Test data shape: {X_test.shape}")
    else:
        print("No test competition ID or year provided. Using train/test split.")
        data = prepare_data(remove_draws, training_data_filter)
        X_train, X_test, y_train, y_test = train_test_split(
            data.drop('result', axis=1), 
            data['result'],
            test_size=0.2,
            random_state=42
        )
    
    # Create a validation set from training data
    X_train, X_dev, y_train, y_dev = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42
    )
    
    # Prepare data for neural network (standardization is important)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_dev_scaled = scaler.transform(X_dev)
    X_test_scaled = scaler.transform(X_test)
    
    # Convert labels to numeric
    label_map = {'win': 0, 'draw': 1, 'loss': 2}
    y_train_encoded = np.array([label_map[label] for label in y_train])
    y_dev_encoded = np.array([label_map[label] for label in y_dev])
    y_test_encoded = np.array([label_map[label] for label in y_test])
    
    # Convert to PyTorch tensors
    X_train_tensor = torch.FloatTensor(X_train_scaled)
    y_train_tensor = torch.LongTensor(y_train_encoded)
    X_dev_tensor = torch.FloatTensor(X_dev_scaled)
    y_dev_tensor = torch.LongTensor(y_dev_encoded)
    X_test_tensor = torch.FloatTensor(X_test_scaled)
    y_test_tensor = torch.LongTensor(y_test_encoded)
    
    # Create DataLoaders
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    # Initialize model
    input_size = X_train.shape[1]
    model = FootballNN(input_size=input_size)
    
    # Define loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )
    
    # Training loop
    num_epochs = 100
    train_losses = []
    dev_losses = []
    best_dev_loss = float('inf')
    best_model_state = None
    patience = 10
    patience_counter = 0
    
    print("Starting training...")
    for epoch in range(num_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # Validation phase
        model.eval()
        with torch.no_grad():
            dev_outputs = model(X_dev_tensor)
            dev_loss = criterion(dev_outputs, y_dev_tensor).item()
            
            # Track losses
            train_losses.append(train_loss / len(train_loader))
            dev_losses.append(dev_loss)
            
            scheduler.step(dev_loss)
            
            # Print progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {train_losses[-1]:.4f}, Val Loss: {dev_loss:.4f}")
            
            # Save best model
            if dev_loss < best_dev_loss:
                best_dev_loss = dev_loss
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
                
            # Early stopping
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
    
    # Load best model
    model.load_state_dict(best_model_state)
    
    # Plot training curve
    plt.figure(figsize=(10, 5))
    plt.plot(train_losses, label='Training Loss')
    plt.plot(dev_losses, label='Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss')
    plt.legend()
    plt.savefig('neural_network_training_curve.png')
    
    # Evaluation
    model.eval()
    with torch.no_grad():
        # Get predictions
        train_outputs = model(X_train_tensor)
        dev_outputs = model(X_dev_tensor)
        test_outputs = model(X_test_tensor)
        
        # Convert to probabilities
        train_probs = nn.functional.softmax(train_outputs, dim=1).numpy()
        dev_probs = nn.functional.softmax(dev_outputs, dim=1).numpy()
        test_probs = nn.functional.softmax(test_outputs, dim=1).numpy()
        
        # Get predicted labels
        train_preds = np.argmax(train_probs, axis=1)
        dev_preds = np.argmax(dev_probs, axis=1)
        test_preds = np.argmax(test_probs, axis=1)
        
        # Convert back to original labels
        id_to_label = {v: k for k, v in label_map.items()}
        y_train_pred_labels = [id_to_label[pred] for pred in train_preds]
        y_dev_pred_labels = [id_to_label[pred] for pred in dev_preds]
        y_test_pred_labels = [id_to_label[pred] for pred in test_preds]
        
        # Original labels
        y_train_labels = y_train.values
        y_dev_labels = y_dev.values
        y_test_labels = y_test.values
    
    # Print evaluation metrics
    print("\nTrain Confusion Matrix:")
    print(confusion_matrix(y_train_labels, y_train_pred_labels))
    print("\nTrain Classification Report:")
    print(classification_report(y_train_labels, y_train_pred_labels))
    
    print("\nDev Confusion Matrix:")
    print(confusion_matrix(y_dev_labels, y_dev_pred_labels))
    print("\nDev Classification Report:")
    print(classification_report(y_dev_labels, y_dev_pred_labels))
    
    if y_test is not None:
        print("\nTest Confusion Matrix:")
        print(confusion_matrix(y_test_labels, y_test_pred_labels))
        print("\nTest Classification Report:")
        print(classification_report(y_test_labels, y_test_pred_labels))
    
    # Print accuracy scores
    print(f"\nTrain Accuracy: {accuracy_score(y_train_labels, y_train_pred_labels):.4f}")
    print(f"Dev Accuracy: {accuracy_score(y_dev_labels, y_dev_pred_labels):.4f}")
    if y_test is not None:
        print(f"Test Accuracy: {accuracy_score(y_test_labels, y_test_pred_labels):.4f}")
    
    # Additional metrics
    print("\nDev Additional Metrics:")
    print(f"- Weighted Avg F1: {classification_report(y_dev_labels, y_dev_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
    print(f"- Macro Avg Precision: {classification_report(y_dev_labels, y_dev_pred_labels, output_dict=True)['macro avg']['precision']:.2f}")

    print("\nTrain Additional Metrics:")
    print(f"- Weighted Avg F1: {classification_report(y_train_labels, y_train_pred_labels, output_dict=True)['weighted avg']['f1-score']:.2f}")
    print(f"- Macro Avg Precision: {classification_report(y_train_labels, y_train_pred_labels, output_dict=True)['macro avg']['precision']:.2f}")
    
    # Create confusion matrix plots
    plt.figure(figsize=(18, 5))
    
    plt.subplot(1, 3, 1)
    sns.heatmap(confusion_matrix(y_train_labels, y_train_pred_labels, normalize='true'),
                annot=True, fmt='.2f', cmap='Blues', xticklabels=label_map.keys(), yticklabels=label_map.keys())
    plt.title('Train Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    
    plt.subplot(1, 3, 2)
    sns.heatmap(confusion_matrix(y_dev_labels, y_dev_pred_labels, normalize='true'),
                annot=True, fmt='.2f', cmap='Blues', xticklabels=label_map.keys(), yticklabels=label_map.keys())
    plt.title('Dev Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    
    if y_test is not None:
        plt.subplot(1, 3, 3)
        sns.heatmap(confusion_matrix(y_test_labels, y_test_pred_labels, normalize='true'),
                    annot=True, fmt='.2f', cmap='Blues', xticklabels=label_map.keys(), yticklabels=label_map.keys())
        plt.title('Test Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
    
    plt.tight_layout()
    plt.savefig('neural_network_confusion_matrices.png')
    
    return model, scaler, label_map


def predict_with_nn(model, scaler, label_map, X):
    """
    Predict using the trained neural network
    
    Args:
        model: Trained neural network model
        scaler: StandardScaler used during training
        label_map: Mapping from numeric labels to string labels
        X: DataFrame with features
    
    Returns:
        Predictions and probabilities
    """
    # Prepare data
    X, _ = prepare_data_for_inference(X)
    
    # Scale data
    X_scaled = scaler.transform(X)
    X_tensor = torch.FloatTensor(X_scaled)
    
    # Get predictions
    model.eval()
    with torch.no_grad():
        outputs = model(X_tensor)
        probabilities = nn.functional.softmax(outputs, dim=1).numpy()
        predicted_classes = np.argmax(probabilities, axis=1)
    
    # Convert numeric predictions to labels
    id_to_label = {v: k for k, v in label_map.items()}
    predictions = [id_to_label[pred] for pred in predicted_classes]
    
    return predictions, probabilities


if __name__ == "__main__":
    # Example usage
    model, scaler, label_map = neural_network_model(
        remove_draws=False,
        training_data_filter=[61,140,39,78,2,3]  # Premier League, La Liga, Bundesliga
    )