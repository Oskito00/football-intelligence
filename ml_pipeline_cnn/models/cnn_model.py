"""
CNN model for football match prediction
Uses convolutional layers to process sequential match data
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
import logging

class FootballCNN(nn.Module):
    """
    CNN model for football match prediction
    Processes sequential match data (form and H2H) along with traditional features
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CNN model
        
        Args:
            config: Model configuration
        """
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Form sequence processing (10 matches, 2 features each)
        self.form_conv1 = nn.Conv1d(4, 32, kernel_size=3, padding=1)
        self.form_conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.form_pool = nn.MaxPool1d(2)
        
        # H2H sequence processing (10 matches, 2 features each)
        self.h2h_conv1 = nn.Conv1d(2, 32, kernel_size=3, padding=1)
        self.h2h_conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.h2h_pool = nn.MaxPool1d(2)
        
        # Calculate sizes after convolutions and pooling
        # For 10 matches:
        # After first conv: 10 matches
        # After first pool: 5 matches
        # After second conv: 5 matches
        # After second pool: 2 matches
        form_seq_size = 64 * 2  # 64 filters * 2 matches
        h2h_seq_size = 64 * 2   # 64 filters * 2 matches
        
        # Traditional features processing
        self.traditional_fc1 = nn.Linear(config['model']['architecture']['traditional_features_size'], 128)
        
        # Combine all features
        combined_size = form_seq_size + h2h_seq_size + 128
        self.fc1 = nn.Linear(combined_size, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 3)  # 3 classes: home win, draw, away win
        
        # Dropout for regularization
        self.dropout = nn.Dropout(0.3)
        
    def forward(self, traditional_features: torch.Tensor, 
                form_sequences: torch.Tensor, 
                h2h_sequences: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network
        
        Args:
            traditional_features: Traditional features tensor
            form_sequences: Form sequence tensor
            h2h_sequences: H2H sequence tensor
            
        Returns:
            Model predictions
        """
        # Process form sequences
        form = form_sequences.transpose(1, 2)  # (batch, channels, sequence)
        form = F.relu(self.form_conv1(form))
        form = self.form_pool(form)
        form = F.relu(self.form_conv2(form))
        form = self.form_pool(form)
        form = form.view(form.size(0), -1)  # Flatten
        
        # Process H2H sequences
        h2h = h2h_sequences.transpose(1, 2)  # (batch, channels, sequence)
        h2h = F.relu(self.h2h_conv1(h2h))
        h2h = self.h2h_pool(h2h)
        h2h = F.relu(self.h2h_conv2(h2h))
        h2h = self.h2h_pool(h2h)
        h2h = h2h.view(h2h.size(0), -1)  # Flatten
        
        # Process traditional features
        traditional = F.relu(self.traditional_fc1(traditional_features))
        
        # Combine all features
        combined = torch.cat([form, h2h, traditional], dim=1)
        
        # Final layers
        x = F.relu(self.fc1(combined))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        
        return x

class CNNModel:
    """
    Wrapper class for the CNN model with training and evaluation methods
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model wrapper
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = FootballCNN(config).to(self.device)
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=config['training']['learning_rate']
        )
        self.criterion = nn.CrossEntropyLoss()
        
    def train(self, traditional_features: pd.DataFrame, 
              form_sequences: np.ndarray, 
              h2h_sequences: np.ndarray,
              targets: np.ndarray,
              validation_split: float = 0.2) -> Dict[str, Any]:
        """
        Train the model
        
        Args:
            traditional_features: Traditional features DataFrame
            form_sequences: Form sequence array
            h2h_sequences: H2H sequence array
            targets: Target labels
            validation_split: Validation split ratio
            
        Returns:
            Training history
        """
        self.logger.info("Starting model training")
        
        # Convert data to tensors
        traditional_tensor = torch.FloatTensor(traditional_features.values).to(self.device)
        form_tensor = torch.FloatTensor(form_sequences).to(self.device)
        h2h_tensor = torch.FloatTensor(h2h_sequences).to(self.device)
        targets_tensor = torch.LongTensor(targets).to(self.device)
        
        # Create validation split
        val_size = int(len(targets) * validation_split)
        train_size = len(targets) - val_size
        
        indices = torch.randperm(len(targets))
        train_indices = indices[:train_size]
        val_indices = indices[train_size:]
        
        # Training loop
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': []
        }
        
        for epoch in range(self.config['training']['epochs']):
            # Training phase
            self.model.train()
            train_loss = 0
            train_correct = 0
            
            for i in range(0, train_size, self.config['training']['batch_size']):
                batch_indices = train_indices[i:i + self.config['training']['batch_size']]
                
                # Forward pass
                outputs = self.model(
                    traditional_tensor[batch_indices],
                    form_tensor[batch_indices],
                    h2h_tensor[batch_indices]
                )
                
                loss = self.criterion(outputs, targets_tensor[batch_indices])
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                train_loss += loss.item()
                train_correct += (outputs.argmax(dim=1) == targets_tensor[batch_indices]).sum().item()
            
            # Validation phase
            self.model.eval()
            val_loss = 0
            val_correct = 0
            
            with torch.no_grad():
                for i in range(0, val_size, self.config['training']['batch_size']):
                    batch_indices = val_indices[i:i + self.config['training']['batch_size']]
                    
                    outputs = self.model(
                        traditional_tensor[batch_indices],
                        form_tensor[batch_indices],
                        h2h_tensor[batch_indices]
                    )
                    
                    loss = self.criterion(outputs, targets_tensor[batch_indices])
                    val_loss += loss.item()
                    val_correct += (outputs.argmax(dim=1) == targets_tensor[batch_indices]).sum().item()
            
            # Calculate metrics
            train_loss /= (train_size / self.config['training']['batch_size'])
            val_loss /= (val_size / self.config['training']['batch_size'])
            train_acc = train_correct / train_size
            val_acc = val_correct / val_size
            
            # Update history
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            self.logger.info(f"Epoch {epoch+1}/{self.config['training']['epochs']} - "
                           f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f} - "
                           f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        return history
    
    def predict(self, traditional_features: pd.DataFrame,
                form_sequences: np.ndarray,
                h2h_sequences: np.ndarray) -> np.ndarray:
        """
        Make predictions
        
        Args:
            traditional_features: Traditional features DataFrame
            form_sequences: Form sequence array
            h2h_sequences: H2H sequence array
            
        Returns:
            Predictions
        """
        self.model.eval()
        
        with torch.no_grad():
            traditional_tensor = torch.FloatTensor(traditional_features.values).to(self.device)
            form_tensor = torch.FloatTensor(form_sequences).to(self.device)
            h2h_tensor = torch.FloatTensor(h2h_sequences).to(self.device)
            
            outputs = self.model(traditional_tensor, form_tensor, h2h_tensor)
            predictions = outputs.argmax(dim=1).cpu().numpy()
        
        return predictions
    
    def save(self, path: str):
        """Save model state"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config
        }, path)
    
    def load(self, path: str):
        """Load model state"""
        checkpoint = torch.load(path)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.config = checkpoint['config'] 