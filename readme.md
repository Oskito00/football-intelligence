# Football Prediction ML Pipeline

A comprehensive machine learning pipeline for football match prediction, featuring modular architecture, feature versioning, and separate training/inference workflows.

## 🏗️ Architecture Overview

```
your_project/
│
├── ml_pipeline/                  # Core ML logic
│   ├── training/                 # Training-specific code
│   │   ├── train_result_model.py
│   │   └── train_goal_scorer_model.py (TODO)
│   │
│   ├── inference/               # Inference logic
│   │   ├── infer_result_model.py
│   │   └── infer_goal_scorer_model.py (TODO)
│   │
│   ├── models/                  # Model definitions & wrappers
│   │   ├── base_model.py
│   │   ├── result_model.py
│   │   └── goal_scorer_model.py (TODO)
│   │
│   ├── features/                # Feature loading & engineering
│   │   ├── base_feature_loader.py
│   │   ├── load_result_features.py
│   │   └── load_goal_scorer_features.py (TODO)
│   │
│   ├── evaluation/             # Metrics, validation, analysis
│   │   ├── evaluate_predictions.py
│   │   └── cross_validation.py (TODO)
│   │
│   └── utils/                  # Shared helpers
│       ├── io.py               # save/load model, features, config
│       ├── config.py           # YAML/JSON config management
│       └── logging.py (TODO)
│
├── configs/                    # Config files per model
│   ├── result_model.yaml
│   └── goal_scorer_model.yaml (TODO)
│
├── data/                       # Feature files, datasets
├── saved_models/              # Trained model files
├── notebooks/                 # Prototyping (TODO)
├── main_train.py              # Entry point to train
├── main_infer.py              # Entry point to infer
└── README.md
```

## 🔧 Key Features

### 1. **Feature Store / Feature Management**
- Features are extracted into separate database tables
- Feature versioning and consistency between training and inference
- Configurable feature loading based on model requirements

### 2. **Training Pipeline**
- Loads features and labels based on configuration
- Supports multiple algorithms (XGBoost, Random Forest, Logistic Regression)
- Cross-validation and model evaluation
- Automatic model saving with metadata

### 3. **Inference Pipeline**
- Loads trained models and applies same preprocessing
- Ensures feature consistency with training
- Batch prediction with confidence scores
- Automatic result saving

### 4. **Configuration-Driven**
- YAML/JSON configuration files for each model
- Easy experiment management and reproducibility
- Configurable data filters, preprocessing, and model parameters

## 🚀 Quick Start

### Prerequisites

```bash
# Install required packages
pip install pandas numpy scikit-learn xgboost psycopg2-binary pyyaml joblib
```

### Training a Model

```bash
# Train the result prediction model
python main_train.py result_model

# Train with specific options
python main_train.py result_model --limit 10000 --dry-run
```

### Running Inference

```bash
# Run inference with latest model
python main_infer.py result_model

# Run inference with specific model version
python main_infer.py result_model --model-version 20241201_143022

# Save predictions to file
python main_infer.py result_model --output predictions.csv
```

## 📊 Models

### Result Model
**Purpose**: Predicts match outcomes (home win, draw, away win)

**Features**:
- ELO ratings (multiple K values)
- Team fatigue metrics (matches in last N days)
- Stage of season
- Team formations
- Competition information

**Target**: Match result (categorical: home_win, draw, away_win)

**Configuration**: `configs/result_model.yaml`

### Goal Scorer Model (TODO)
**Purpose**: Predicts which players will score in a match

## 🔧 Configuration

Each model has its own configuration file in the `configs/` directory. Here's an example:

```yaml
# configs/result_model.yaml
model:
  name: "result_model"
  type: "classification"
  algorithm: "xgboost"
  hyperparameters:
    n_estimators: 100
    max_depth: 6
    learning_rate: 0.1

data:
  feature_loader: "load_result_features"
  target_column: "result"
  feature_tables:
    - "elo_history"
    - "fatigue_history"
    - "stage_of_season_history"
  filters:
    min_date: "2020-01-01"
  test_size: 0.2

preprocessing:
  scale_features: true
  handle_missing: true
  
training:
  cross_validation:
    enabled: true
    folds: 5
```

## 🏋️ Training Process

1. **Load Configuration**: Parse YAML config for model specifications
2. **Initialize Feature Loader**: Set up database connections and feature extraction
3. **Load Data**: Extract features and targets based on configuration
4. **Data Quality Check**: Validate data and report quality metrics
5. **Data Cleaning**: Handle missing values, outliers, and duplicates
6. **Train/Test Split**: Split data maintaining class balance
7. **Preprocessing**: Scale features and apply transformations
8. **Model Training**: Train with cross-validation if enabled
9. **Evaluation**: Compute metrics and generate reports
10. **Model Saving**: Save model, preprocessor, and metadata

## 🔍 Inference Process

1. **Load Model**: Retrieve trained model and preprocessor
2. **Load Features**: Extract features for new data
3. **Feature Alignment**: Ensure features match training schema
4. **Preprocessing**: Apply same transformations as training
5. **Prediction**: Generate predictions and confidence scores
6. **Output**: Save results and return predictions

## 📈 Evaluation

The pipeline provides comprehensive evaluation metrics:

- **Classification Metrics**: Accuracy, Precision, Recall, F1-score
- **Confusion Matrix**: Visual representation of prediction errors
- **ROC AUC**: Area under ROC curve for multi-class classification
- **Feature Importance**: Most important features for predictions
- **Cross-Validation**: K-fold validation scores

## 🔧 Feature Engineering

### Automatic Feature Engineering
- **ELO Differences**: Home team ELO - Away team ELO
- **Fatigue Differences**: Difference in rest days between teams
- **Formation Encoding**: One-hot encoding of common formations
- **Competition Encoding**: Categorical encoding of competitions

### Custom Feature Engineering
Add custom feature engineering in the feature loader classes:

```python
def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
    # Add custom features here
    df['custom_feature'] = df['feature1'] * df['feature2']
    return df
```

## 📂 Data Management

### Feature Storage
- Features are stored in separate database tables
- Each table corresponds to a specific feature type (ELO, fatigue, etc.)
- Features are versioned through timestamps

### Model Storage
- Models are saved with timestamps in `saved_models/`
- Includes model, preprocessor, and metadata
- Symbolic links point to latest versions

### Prediction Storage
- Predictions can be saved to CSV files
- Include probabilities and timestamps
- Can be integrated back to database

## 🧪 Development Workflow

### Adding a New Model

1. **Create Configuration**:
   ```bash
   cp configs/result_model.yaml configs/new_model.yaml
   # Edit configuration for your model
   ```

2. **Create Feature Loader**:
   ```python
   # ml_pipeline/features/load_new_model_features.py
   class NewModelFeatureLoader(BaseFeatureLoader):
       def get_required_tables(self):
           return ['table1', 'table2']
       
       def load_features(self, where_clause=None, limit=None):
           # Implement feature loading logic
           pass
   ```

3. **Create Model Class**:
   ```python
   # ml_pipeline/models/new_model.py
   class NewModel(BaseModel):
       def create_model(self):
           # Implement model creation
           pass
   ```

4. **Create Training Module**:
   ```python
   # ml_pipeline/training/train_new_model.py
   def train_new_model(conn, config, dry_run=False, limit=None):
       # Implement training logic
       pass
   ```

5. **Update Entry Points**:
   ```python
   # main_train.py
   trainers = {
       'result_model': train_result_model,
       'new_model': train_new_model,  # Add this line
   }
   ```

### Running Tests

```bash
# TODO: Add test framework
python -m pytest tests/
```

## 🐛 Troubleshooting

### Common Issues

1. **Missing Tables**: Ensure all required feature tables exist in database
2. **Feature Mismatch**: Check that inference features match training features
3. **Memory Issues**: Use `--limit` parameter for testing with smaller datasets
4. **Configuration Errors**: Validate YAML syntax and required fields

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main_train.py result_model
```

## 📋 TODO

- [ ] Add goal scorer prediction model
- [ ] Implement neural network models
- [ ] Add automated hyperparameter tuning
- [ ] Create Jupyter notebooks for analysis
- [ ] Add comprehensive test suite
- [ ] Implement model monitoring and drift detection
- [ ] Add Docker containerization
- [ ] Create web API for real-time predictions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

#Contributors
Oscar Alberigo, William Boyd

