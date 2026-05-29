.PHONY: scrape process-history build-future predict odds

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
