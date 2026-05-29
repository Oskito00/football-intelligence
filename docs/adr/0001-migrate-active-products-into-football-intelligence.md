# Migrate Active Products Into Football Intelligence

The active product code for the **Match Intelligence Lifecycle** and **Analyst Agent** lives under `football_intelligence.*`; implementation-era packages such as `data_scraping`, `data_processing`, `ml_pipeline`, `utils.database`, `chatbot`, and `scheduler` are temporary migration sources, not long-term public architecture. We will move active behavior into the product namespace, update runtime entrypoints to the new modules, and delete old internal packages once active callers have moved instead of preserving long-lived compatibility shims.

Saved model artifacts are product assets rather than Python package code, so they will move to root-level `models/`. Prediction behavior configs belong with prediction code and will move to `football_intelligence/predictions/configs/`.
