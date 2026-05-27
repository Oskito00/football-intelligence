"""Compatibility entrypoint for Future Feature Set processing."""

from football_intelligence.features import build_future_feature_set


def process_future_matches(conn):
    return build_future_feature_set(conn)
