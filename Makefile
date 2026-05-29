.PHONY: db-setup db-upgrade db-current db-stamp-baseline status tonight scrape process-history build-future predict odds

db-setup:
	python -m football_intelligence.cli db setup

db-upgrade:
	python -m football_intelligence.cli db upgrade

db-current:
	python -m football_intelligence.cli db current

db-stamp-baseline:
	python -m football_intelligence.cli db stamp-baseline

status:
	python -m football_intelligence.cli status

tonight:
	python -m football_intelligence.cli board today

scrape:
	python -m football_intelligence.cli prediction-refresh --only source-data-ingestion

process-history:
	python -m football_intelligence.cli prediction-refresh --only historical-feature-set

build-future:
	python -m football_intelligence.cli prediction-refresh --only future-feature-set

predict:
	python -m football_intelligence.cli prediction-refresh --only prediction-inference

odds:
	python -m football_intelligence.cli prediction-refresh --only odds-refresh
