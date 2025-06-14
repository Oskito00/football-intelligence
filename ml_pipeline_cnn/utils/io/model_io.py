"""
Model IO utilities for saving and loading CNN models
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import torch

logger = logging.getLogger(__name__)

def save_model(model: torch.nn.Module, 
              model_name: str,
              metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Save model state and metadata
    
    Args:
        model: PyTorch model to save
        model_name: Name of the model
        metadata: Optional metadata to save with the model
        
    Returns:
        Path to saved model
    """
    # Create save directory
    save_dir = os.path.join('ml_pipeline_cnn', 'saved_models', model_name)
    os.makedirs(save_dir, exist_ok=True)
    
    # Save model state
    model_path = os.path.join(save_dir, 'model.pt')
    torch.save(model.state_dict(), model_path)
    
    # Save metadata if provided
    if metadata:
        metadata_path = os.path.join(save_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    logger.info(f"Model saved to {save_dir}")
    return save_dir


def load_model(model: torch.nn.Module,
              model_name: str) -> Dict[str, Any]:
    """
    Load model state and metadata
    
    Args:
        model: PyTorch model to load state into
        model_name: Name of the model to load
        
    Returns:
        Dictionary containing model metadata
    """
    # Get save directory
    save_dir = os.path.join('ml_pipeline_cnn', 'saved_models', model_name)
    
    # Load model state
    model_path = os.path.join(save_dir, 'model.pt')
    model.load_state_dict(torch.load(model_path))
    
    # Load metadata
    metadata_path = os.path.join(save_dir, 'metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    logger.info(f"Model loaded from {save_dir}")
    return metadata 