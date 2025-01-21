import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

class MatchPredictor(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 3),
            nn.Softmax(dim=1)
        )
    
    def forward(self, x):
        return self.model(x)

def train_epoch(model, train_loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    for inputs, targets in tqdm(train_loader, desc="Training"):
        inputs, targets = inputs.to(device), targets.to(device)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
    
    return total_loss / len(train_loader), correct / total

def validate(model, val_loader, criterion, device):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            
            total_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
    
    return total_loss / len(val_loader), correct / total

def run_neural_network(n_runs=100, epochs=100):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    metrics = {
        'accuracies': [],
        'draw_precision': [],
        'draw_recall': [],
        'draw_f1': [],
        'home_precision': [],
        'home_recall': [],
        'home_f1': [],
        'away_precision': [],
        'away_recall': [],
        'away_f1': [],
        'val_accuracies': []
    }
    
    for run_i in range(n_runs):
        print(f"\n{'='*60}")
        print(f"Run {run_i+1}/{n_runs}")
        print(f"{'='*60}")
        
        # Load and prepare data
        print("Loading and preparing data...")
        df = pd.read_csv("sportradar/AI/preprocessed_features.csv")
        
        df["outcome"] = [2 if h > a else (1 if h == a else 0) 
                        for h, a in zip(df["home_goals"], df["away_goals"])]
        
        metadata_cols = ["start_time", "home_team", "away_team", "home_goals", "away_goals", "outcome"]
        X = df.drop(columns=metadata_cols)
        y = df["outcome"]
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=np.random.randint(0, 1000)
        )
        
        # Convert to PyTorch tensors
        X_train = torch.FloatTensor(X_train)
        y_train = torch.LongTensor(y_train.values)
        X_test = torch.FloatTensor(X_test)
        y_test = torch.LongTensor(y_test.values)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        test_dataset = TensorDataset(X_test, y_test)
        test_loader = DataLoader(test_dataset, batch_size=32)
        
        # Create model
        model = MatchPredictor(X_train.shape[1]).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        # Training loop
        best_val_acc = 0
        patience = 10
        patience_counter = 0
        
        print("\nTraining model...")
        for epoch in range(epochs):
            train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc = validate(model, test_loader, criterion, device)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}")
                print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2%}")
                print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2%}")
        
        # Final evaluation
        model.eval()
        with torch.no_grad():
            y_pred = model(X_test.to(device)).cpu()
            y_pred = torch.argmax(y_pred, dim=1).numpy()
        
        # Calculate metrics
        accuracy = accuracy_score(y_test.numpy(), y_pred)
        metrics['accuracies'].append(accuracy)
        metrics['val_accuracies'].append(best_val_acc)
        
        for outcome in [0, 1, 2]:
            precision = precision_score(y_test.numpy() == outcome, y_pred == outcome, zero_division=0)
            recall = recall_score(y_test.numpy() == outcome, y_pred == outcome, zero_division=0)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            if outcome == 0:
                metrics['away_precision'].append(precision)
                metrics['away_recall'].append(recall)
                metrics['away_f1'].append(f1)
            elif outcome == 1:
                metrics['draw_precision'].append(precision)
                metrics['draw_recall'].append(recall)
                metrics['draw_f1'].append(f1)
            else:
                metrics['home_precision'].append(precision)
                metrics['home_recall'].append(recall)
                metrics['home_f1'].append(f1)
        
        # Print results
        print(f"\nRun {run_i+1} Results:")
        print(f"Test Accuracy: {accuracy:.2%}")
        print(f"Best Validation Accuracy: {best_val_acc:.2%}")
        
        cm = confusion_matrix(y_test.numpy(), y_pred)
        print("\nConfusion Matrix:")
        print("Predicted →  [Away Win  Draw  Home Win]")
        print(f"Actual ↓\n{cm}")
        print("-"*60)
    
    # Print final results
    print("\nFinal Results:")
    print(f"Mean Test Accuracy: {np.mean(metrics['accuracies']):.2%} (±{np.std(metrics['accuracies']):.2%})")
    print(f"Mean Validation Accuracy: {np.mean(metrics['val_accuracies']):.2%} (±{np.std(metrics['val_accuracies']):.2%})")
    
    print("\nClass-specific metrics:")
    for outcome in ['home', 'draw', 'away']:
        print(f"\n{outcome.title()} Predictions:")
        print(f"Precision: {np.mean(metrics[f'{outcome}_precision']):.2%} (±{np.std(metrics[f'{outcome}_precision']):.2%})")
        print(f"Recall: {np.mean(metrics[f'{outcome}_recall']):.2%} (±{np.std(metrics[f'{outcome}_recall']):.2%})")
        print(f"F1: {np.mean(metrics[f'{outcome}_f1']):.2%} (±{np.std(metrics[f'{outcome}_f1']):.2%})")
    
    return metrics

if __name__ == "__main__":
    print("Training Neural Network Model:")
    metrics = run_neural_network(n_runs=100) 