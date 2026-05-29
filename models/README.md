# Local Model Artifacts

This directory is the default local home for generated model artifacts.

The public repository does not ship trained `.pkl`, `.joblib`, metadata, or
preprocessor files. Run **Model Training** locally when you want to create
artifacts for prediction inference:

```bash
python -m football_intelligence.cli model-training
```

Generated files in this directory are intentionally ignored by Git.
