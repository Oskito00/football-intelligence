# Use Alembic For Database Setup

Alembic is the canonical **Database Setup** mechanism for Football
Intelligence. It owns schema creation and upgrades for the application database,
starting from an explicit baseline of the current schema and continuing through
versioned migrations for later schema changes.

API startup is read-only. Starting the API or opening read-only inspection
surfaces does not create, migrate, or mutate schema. If required schema objects
are missing, read-only surfaces should report a clear setup-required condition
rather than hiding schema ownership behind runtime table creation.

Operational workflows assume **Database Setup** has already run. **Source Data
Ingestion**, **Prediction Refresh**, **Model Training**, **Football Data
Status**, the **Prediction Board**, **Market Value Signals**, and **Feature
Snapshots** depend on the schema prepared by Alembic instead of opportunistic
`CREATE TABLE IF NOT EXISTS` behavior.

All new schema changes must be expressed as Alembic migrations. Compatibility
helpers may remain temporarily while older workflows are moved across, but they
are bridges rather than the long-term schema contract.

Schema is source-controlled migration code, not generated data. Database dumps,
local exports, trained model files, and other runtime artifacts are not part of
the canonical schema history.
