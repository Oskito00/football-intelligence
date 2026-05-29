"""Baseline Football Intelligence schema.

Revision ID: 0001_baseline_schema
Revises: 
Create Date: 2026-05-29
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0001_baseline_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BASELINE_SCHEMA_SQL = r"""
CREATE TABLE club_elo_ratings (
    team_id integer NOT NULL,
    team_name text,
    elo_home_matches_k5 integer,
    elo_home_matches_k10 integer,
    elo_home_matches_k20 integer,
    elo_home_matches_k30 integer,
    elo_home_matches_k40 integer,
    elo_home_matches_k80 integer,
    elo_away_matches_k5 integer,
    elo_away_matches_k10 integer,
    elo_away_matches_k20 integer,
    elo_away_matches_k30 integer,
    elo_away_matches_k40 integer,
    elo_away_matches_k80 integer,
    elo_k5 integer,
    elo_k10 integer,
    elo_k20 integer,
    elo_k30 integer,
    elo_k40 integer,
    elo_k80 integer,
    elo_domestic_k5 integer,
    elo_domestic_k10 integer,
    elo_domestic_k20 integer,
    elo_domestic_k30 integer,
    elo_domestic_k40 integer,
    elo_domestic_k80 integer,
    elo_intraleague_k5 integer,
    elo_intraleague_k10 integer,
    elo_intraleague_k20 integer,
    elo_intraleague_k30 integer,
    elo_intraleague_k40 integer,
    elo_intraleague_k80 integer,
    elo_international_k5 integer,
    elo_international_k10 integer,
    elo_international_k20 integer,
    elo_international_k30 integer,
    elo_international_k40 integer,
    elo_international_k80 integer
);
CREATE TABLE continent_elo_ratings (
    continent_name text NOT NULL,
    continent_elo_k5 integer,
    continent_elo_k10 integer,
    continent_elo_k20 integer,
    continent_elo_k30 integer,
    continent_elo_k40 integer,
    continent_elo_k80 integer
);
CREATE TABLE counter_table (
    competition_id text NOT NULL,
    home_wins double precision,
    draw_wins double precision,
    away_wins double precision,
    count integer,
    last_updated text
);
CREATE TABLE elo_future (
    match_id integer,
    start_time timestamp without time zone,
    home_team_id integer,
    away_team_id integer,
    home_team_name text,
    away_team_name text,
    k_draw_parameter real,
    eta_home_advantage real,
    home_team_nation_elo_k5 integer,
    home_team_nation_elo_k10 integer,
    home_team_nation_elo_k20 integer,
    home_team_nation_elo_k30 integer,
    home_team_nation_elo_k40 integer,
    home_team_nation_elo_k80 integer,
    home_team_league_domestic_elo_k5 integer,
    home_team_league_domestic_elo_k10 integer,
    home_team_league_domestic_elo_k20 integer,
    home_team_league_domestic_elo_k30 integer,
    home_team_league_domestic_elo_k40 integer,
    home_team_league_domestic_elo_k80 integer,
    home_team_league_continental_elo_k5 integer,
    home_team_league_continental_elo_k10 integer,
    home_team_league_continental_elo_k20 integer,
    home_team_league_continental_elo_k30 integer,
    home_team_league_continental_elo_k40 integer,
    home_team_league_continental_elo_k80 integer,
    home_team_league_intercontinental_elo_k5 integer,
    home_team_league_intercontinental_elo_k10 integer,
    home_team_league_intercontinental_elo_k20 integer,
    home_team_league_intercontinental_elo_k30 integer,
    home_team_league_intercontinental_elo_k40 integer,
    home_team_league_intercontinental_elo_k80 integer,
    home_team_continent_elo_k5 integer,
    home_team_continent_elo_k10 integer,
    home_team_continent_elo_k20 integer,
    home_team_continent_elo_k30 integer,
    home_team_continent_elo_k40 integer,
    home_team_continent_elo_k80 integer,
    home_team_elo_home_matches_k5 integer,
    home_team_elo_home_matches_k10 integer,
    home_team_elo_home_matches_k20 integer,
    home_team_elo_home_matches_k30 integer,
    home_team_elo_home_matches_k40 integer,
    home_team_elo_home_matches_k80 integer,
    home_team_elo_away_matches_k5 integer,
    home_team_elo_away_matches_k10 integer,
    home_team_elo_away_matches_k20 integer,
    home_team_elo_away_matches_k30 integer,
    home_team_elo_away_matches_k40 integer,
    home_team_elo_away_matches_k80 integer,
    home_team_elo_k5 integer,
    home_team_elo_k10 integer,
    home_team_elo_k20 integer,
    home_team_elo_k30 integer,
    home_team_elo_k40 integer,
    home_team_elo_k80 integer,
    home_team_elo_domestic_k5 integer,
    home_team_elo_domestic_k10 integer,
    home_team_elo_domestic_k20 integer,
    home_team_elo_domestic_k30 integer,
    home_team_elo_domestic_k40 integer,
    home_team_elo_domestic_k80 integer,
    home_team_elo_intraleague_k5 integer,
    home_team_elo_intraleague_k10 integer,
    home_team_elo_intraleague_k20 integer,
    home_team_elo_intraleague_k30 integer,
    home_team_elo_intraleague_k40 integer,
    home_team_elo_intraleague_k80 integer,
    home_team_elo_international_k5 integer,
    home_team_elo_international_k10 integer,
    home_team_elo_international_k20 integer,
    home_team_elo_international_k30 integer,
    home_team_elo_international_k40 integer,
    home_team_elo_international_k80 integer,
    away_team_nation_elo_k5 integer,
    away_team_nation_elo_k10 integer,
    away_team_nation_elo_k20 integer,
    away_team_nation_elo_k30 integer,
    away_team_nation_elo_k40 integer,
    away_team_nation_elo_k80 integer,
    away_team_league_domestic_elo_k5 integer,
    away_team_league_domestic_elo_k10 integer,
    away_team_league_domestic_elo_k20 integer,
    away_team_league_domestic_elo_k30 integer,
    away_team_league_domestic_elo_k40 integer,
    away_team_league_domestic_elo_k80 integer,
    away_team_league_continental_elo_k5 integer,
    away_team_league_continental_elo_k10 integer,
    away_team_league_continental_elo_k20 integer,
    away_team_league_continental_elo_k30 integer,
    away_team_league_continental_elo_k40 integer,
    away_team_league_continental_elo_k80 integer,
    away_team_league_intercontinental_elo_k5 integer,
    away_team_league_intercontinental_elo_k10 integer,
    away_team_league_intercontinental_elo_k20 integer,
    away_team_league_intercontinental_elo_k30 integer,
    away_team_league_intercontinental_elo_k40 integer,
    away_team_league_intercontinental_elo_k80 integer,
    away_team_continent_elo_k5 integer,
    away_team_continent_elo_k10 integer,
    away_team_continent_elo_k20 integer,
    away_team_continent_elo_k30 integer,
    away_team_continent_elo_k40 integer,
    away_team_continent_elo_k80 integer,
    away_team_elo_home_matches_k5 integer,
    away_team_elo_home_matches_k10 integer,
    away_team_elo_home_matches_k20 integer,
    away_team_elo_home_matches_k30 integer,
    away_team_elo_home_matches_k40 integer,
    away_team_elo_home_matches_k80 integer,
    away_team_elo_away_matches_k5 integer,
    away_team_elo_away_matches_k10 integer,
    away_team_elo_away_matches_k20 integer,
    away_team_elo_away_matches_k30 integer,
    away_team_elo_away_matches_k40 integer,
    away_team_elo_away_matches_k80 integer,
    away_team_elo_k5 integer,
    away_team_elo_k10 integer,
    away_team_elo_k20 integer,
    away_team_elo_k30 integer,
    away_team_elo_k40 integer,
    away_team_elo_k80 integer,
    away_team_elo_domestic_k5 integer,
    away_team_elo_domestic_k10 integer,
    away_team_elo_domestic_k20 integer,
    away_team_elo_domestic_k30 integer,
    away_team_elo_domestic_k40 integer,
    away_team_elo_domestic_k80 integer,
    away_team_elo_intraleague_k5 integer,
    away_team_elo_intraleague_k10 integer,
    away_team_elo_intraleague_k20 integer,
    away_team_elo_intraleague_k30 integer,
    away_team_elo_intraleague_k40 integer,
    away_team_elo_intraleague_k80 integer,
    away_team_elo_international_k5 integer,
    away_team_elo_international_k10 integer,
    away_team_elo_international_k20 integer,
    away_team_elo_international_k30 integer,
    away_team_elo_international_k40 integer,
    away_team_elo_international_k80 integer
);
CREATE TABLE elo_history (
    match_id integer,
    start_time timestamp without time zone,
    home_team_id integer,
    away_team_id integer,
    home_team_name text,
    away_team_name text,
    k_draw_parameter real,
    eta_home_advantage real,
    home_team_nation_elo_k5 integer,
    home_team_nation_elo_k10 integer,
    home_team_nation_elo_k20 integer,
    home_team_nation_elo_k30 integer,
    home_team_nation_elo_k40 integer,
    home_team_nation_elo_k80 integer,
    home_team_league_domestic_elo_k5 integer,
    home_team_league_domestic_elo_k10 integer,
    home_team_league_domestic_elo_k20 integer,
    home_team_league_domestic_elo_k30 integer,
    home_team_league_domestic_elo_k40 integer,
    home_team_league_domestic_elo_k80 integer,
    home_team_league_continental_elo_k5 integer,
    home_team_league_continental_elo_k10 integer,
    home_team_league_continental_elo_k20 integer,
    home_team_league_continental_elo_k30 integer,
    home_team_league_continental_elo_k40 integer,
    home_team_league_continental_elo_k80 integer,
    home_team_league_intercontinental_elo_k5 integer,
    home_team_league_intercontinental_elo_k10 integer,
    home_team_league_intercontinental_elo_k20 integer,
    home_team_league_intercontinental_elo_k30 integer,
    home_team_league_intercontinental_elo_k40 integer,
    home_team_league_intercontinental_elo_k80 integer,
    home_team_continent_elo_k5 integer,
    home_team_continent_elo_k10 integer,
    home_team_continent_elo_k20 integer,
    home_team_continent_elo_k30 integer,
    home_team_continent_elo_k40 integer,
    home_team_continent_elo_k80 integer,
    home_team_elo_home_matches_k5 integer,
    home_team_elo_home_matches_k10 integer,
    home_team_elo_home_matches_k20 integer,
    home_team_elo_home_matches_k30 integer,
    home_team_elo_home_matches_k40 integer,
    home_team_elo_home_matches_k80 integer,
    home_team_elo_away_matches_k5 integer,
    home_team_elo_away_matches_k10 integer,
    home_team_elo_away_matches_k20 integer,
    home_team_elo_away_matches_k30 integer,
    home_team_elo_away_matches_k40 integer,
    home_team_elo_away_matches_k80 integer,
    home_team_elo_k5 integer,
    home_team_elo_k10 integer,
    home_team_elo_k20 integer,
    home_team_elo_k30 integer,
    home_team_elo_k40 integer,
    home_team_elo_k80 integer,
    home_team_elo_domestic_k5 integer,
    home_team_elo_domestic_k10 integer,
    home_team_elo_domestic_k20 integer,
    home_team_elo_domestic_k30 integer,
    home_team_elo_domestic_k40 integer,
    home_team_elo_domestic_k80 integer,
    home_team_elo_intraleague_k5 integer,
    home_team_elo_intraleague_k10 integer,
    home_team_elo_intraleague_k20 integer,
    home_team_elo_intraleague_k30 integer,
    home_team_elo_intraleague_k40 integer,
    home_team_elo_intraleague_k80 integer,
    home_team_elo_international_k5 integer,
    home_team_elo_international_k10 integer,
    home_team_elo_international_k20 integer,
    home_team_elo_international_k30 integer,
    home_team_elo_international_k40 integer,
    home_team_elo_international_k80 integer,
    away_team_nation_elo_k5 integer,
    away_team_nation_elo_k10 integer,
    away_team_nation_elo_k20 integer,
    away_team_nation_elo_k30 integer,
    away_team_nation_elo_k40 integer,
    away_team_nation_elo_k80 integer,
    away_team_league_domestic_elo_k5 integer,
    away_team_league_domestic_elo_k10 integer,
    away_team_league_domestic_elo_k20 integer,
    away_team_league_domestic_elo_k30 integer,
    away_team_league_domestic_elo_k40 integer,
    away_team_league_domestic_elo_k80 integer,
    away_team_league_continental_elo_k5 integer,
    away_team_league_continental_elo_k10 integer,
    away_team_league_continental_elo_k20 integer,
    away_team_league_continental_elo_k30 integer,
    away_team_league_continental_elo_k40 integer,
    away_team_league_continental_elo_k80 integer,
    away_team_league_intercontinental_elo_k5 integer,
    away_team_league_intercontinental_elo_k10 integer,
    away_team_league_intercontinental_elo_k20 integer,
    away_team_league_intercontinental_elo_k30 integer,
    away_team_league_intercontinental_elo_k40 integer,
    away_team_league_intercontinental_elo_k80 integer,
    away_team_continent_elo_k5 integer,
    away_team_continent_elo_k10 integer,
    away_team_continent_elo_k20 integer,
    away_team_continent_elo_k30 integer,
    away_team_continent_elo_k40 integer,
    away_team_continent_elo_k80 integer,
    away_team_elo_home_matches_k5 integer,
    away_team_elo_home_matches_k10 integer,
    away_team_elo_home_matches_k20 integer,
    away_team_elo_home_matches_k30 integer,
    away_team_elo_home_matches_k40 integer,
    away_team_elo_home_matches_k80 integer,
    away_team_elo_away_matches_k5 integer,
    away_team_elo_away_matches_k10 integer,
    away_team_elo_away_matches_k20 integer,
    away_team_elo_away_matches_k30 integer,
    away_team_elo_away_matches_k40 integer,
    away_team_elo_away_matches_k80 integer,
    away_team_elo_k5 integer,
    away_team_elo_k10 integer,
    away_team_elo_k20 integer,
    away_team_elo_k30 integer,
    away_team_elo_k40 integer,
    away_team_elo_k80 integer,
    away_team_elo_domestic_k5 integer,
    away_team_elo_domestic_k10 integer,
    away_team_elo_domestic_k20 integer,
    away_team_elo_domestic_k30 integer,
    away_team_elo_domestic_k40 integer,
    away_team_elo_domestic_k80 integer,
    away_team_elo_intraleague_k5 integer,
    away_team_elo_intraleague_k10 integer,
    away_team_elo_intraleague_k20 integer,
    away_team_elo_intraleague_k30 integer,
    away_team_elo_intraleague_k40 integer,
    away_team_elo_intraleague_k80 integer,
    away_team_elo_international_k5 integer,
    away_team_elo_international_k10 integer,
    away_team_elo_international_k20 integer,
    away_team_elo_international_k30 integer,
    away_team_elo_international_k40 integer,
    away_team_elo_international_k80 integer,
    home_team_score integer,
    away_team_score integer
);
CREATE TABLE form_future (
    match_id integer NOT NULL,
    home_team_id integer,
    away_team_id integer,
    home_name character varying(255),
    away_name character varying(255),
    home_team_form jsonb,
    away_team_form jsonb,
    draw_features jsonb
);
CREATE TABLE form_history (
    match_id integer NOT NULL,
    home_team_id integer,
    away_team_id integer,
    home_name character varying(255),
    away_name character varying(255),
    home_team_form jsonb,
    away_team_form jsonb,
    draw_features jsonb
);
CREATE TABLE form_matches_cache (
    match_id integer NOT NULL,
    start_time timestamp without time zone,
    home_team_id integer,
    away_team_id integer,
    home_name character varying(255),
    away_name character varying(255),
    home_score integer,
    away_score integer,
    home_team_elo integer,
    away_team_elo integer,
    home_team_international_elo integer,
    away_team_international_elo integer
);
CREATE TABLE formation_future (
    match_id integer,
    start_time timestamp without time zone,
    home_team_formation text,
    away_team_formation text
);
CREATE TABLE formation_history (
    match_id integer,
    start_time timestamp without time zone,
    home_team_formation text,
    away_team_formation text
);
CREATE TABLE h2h_future (
    match_id integer NOT NULL,
    h2h_draws_last_3 double precision,
    h2h_draws_last_5 double precision,
    h2h_draws_last_10 double precision,
    h2h_home_wins_last_3 double precision,
    h2h_home_wins_last_5 double precision,
    h2h_home_wins_last_10 double precision,
    h2h_away_wins_last_3 double precision,
    h2h_away_wins_last_5 double precision,
    h2h_away_wins_last_10 double precision,
    h2h_avg_total_goals double precision,
    h2h_avg_goal_diff double precision,
    h2h_home_goals_avg_last_3 double precision,
    h2h_home_goals_avg_last_5 double precision,
    h2h_home_goals_avg_last_10 double precision,
    h2h_away_goals_avg_last_3 double precision,
    h2h_away_goals_avg_last_5 double precision,
    h2h_away_goals_avg_last_10 double precision,
    h2h_both_teams_scored_rate double precision,
    h2h_zero_goal_rate double precision,
    raw_h2h_matches jsonb
);
CREATE TABLE h2h_history (
    match_id integer NOT NULL,
    h2h_draws_last_3 double precision,
    h2h_draws_last_5 double precision,
    h2h_draws_last_10 double precision,
    h2h_home_wins_last_3 double precision,
    h2h_home_wins_last_5 double precision,
    h2h_home_wins_last_10 double precision,
    h2h_away_wins_last_3 double precision,
    h2h_away_wins_last_5 double precision,
    h2h_away_wins_last_10 double precision,
    h2h_avg_total_goals double precision,
    h2h_avg_goal_diff double precision,
    h2h_home_goals_avg_last_3 double precision,
    h2h_home_goals_avg_last_5 double precision,
    h2h_home_goals_avg_last_10 double precision,
    h2h_away_goals_avg_last_3 double precision,
    h2h_away_goals_avg_last_5 double precision,
    h2h_away_goals_avg_last_10 double precision,
    h2h_both_teams_scored_rate double precision,
    h2h_zero_goal_rate double precision,
    raw_h2h_matches jsonb
);
CREATE TABLE h2h_stats (
    team_pair_id integer NOT NULL,
    team1_id integer,
    team2_id integer,
    team1_name text,
    team2_name text,
    total_matches integer DEFAULT 0,
    team1_wins integer DEFAULT 0,
    team2_wins integer DEFAULT 0,
    draws integer DEFAULT 0,
    team1_goals integer DEFAULT 0,
    team2_goals integer DEFAULT 0,
    recent_matches jsonb,
    last_updated timestamp without time zone
);
CREATE SEQUENCE h2h_stats_team_pair_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE h2h_stats_team_pair_id_seq OWNED BY h2h_stats.team_pair_id;
CREATE TABLE league_elo_ratings (
    league_id integer NOT NULL,
    league_domestic_elo_k5 integer,
    league_domestic_elo_k10 integer,
    league_domestic_elo_k20 integer,
    league_domestic_elo_k30 integer,
    league_domestic_elo_k40 integer,
    league_domestic_elo_k80 integer,
    league_continental_elo_k5 integer,
    league_continental_elo_k10 integer,
    league_continental_elo_k20 integer,
    league_continental_elo_k30 integer,
    league_continental_elo_k40 integer,
    league_continental_elo_k80 integer,
    league_intercontinental_elo_k5 integer,
    league_intercontinental_elo_k10 integer,
    league_intercontinental_elo_k20 integer,
    league_intercontinental_elo_k30 integer,
    league_intercontinental_elo_k40 integer,
    league_intercontinental_elo_k80 integer
);
CREATE TABLE league_standings_future (
    match_id integer,
    start_time timestamp without time zone,
    home_standing integer,
    home_matches_played integer,
    home_wins integer,
    home_draws integer,
    home_losses integer,
    home_goals_for integer,
    home_goals_against integer,
    home_goal_difference integer,
    home_points integer,
    away_standing integer,
    away_matches_played integer,
    away_wins integer,
    away_draws integer,
    away_losses integer,
    away_goals_for integer,
    away_goals_against integer,
    away_goal_difference integer,
    away_points integer
);
CREATE TABLE leagues (
    id integer NOT NULL,
    name text,
    type text,
    logo text,
    country json,
    years text[],
    seasons json,
    current_season text
);
CREATE TABLE match_info_future (
    match_id integer NOT NULL,
    start_time timestamp without time zone,
    competition_season_name text,
    competition_id text NOT NULL,
    competition_name text,
    competition_country text,
    home_team_name text,
    away_team_name text
);
CREATE TABLE match_info_history (
    match_id integer NOT NULL,
    start_time timestamp without time zone,
    competition_season_name text,
    competition_id text NOT NULL,
    competition_name text,
    competition_country text,
    home_team_name text,
    away_team_name text
);
CREATE TABLE match_result_predictions (
    match_id integer NOT NULL,
    predicted_result integer,
    start_time timestamp without time zone,
    home_team_name text,
    away_team_name text,
    prob_home_win real,
    prob_draw real,
    prob_away_win real,
    model_type text,
    prediction_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE matches (
    match_id bigint NOT NULL,
    start_time timestamp with time zone,
    clean_date date,
    competition_name text,
    competition_id integer,
    competition_country text,
    competition_season_name text,
    competition_season_id text,
    season_start_date date,
    season_end_date date,
    round_info text,
    home_team_id integer,
    home_team_name text,
    home_team_domestic_league_id integer,
    away_team_domestic_league_id integer,
    home_team_domestic_country text,
    away_team_domestic_country text,
    away_team_id integer,
    away_team_name text,
    match_status text,
    home_score integer,
    away_score integer,
    result text,
    all_fixture_data jsonb,
    all_season_info jsonb,
    home_team_formation text,
    away_team_formation text,
    home_team_lineup text,
    away_team_lineup text,
    attempted_formation_scrape boolean DEFAULT false,
    is_current_season boolean,
    has_odds boolean,
    has_players boolean,
    has_lineups boolean,
    has_events boolean,
    has_statistics_players boolean,
    has_statistics_fixtures boolean
);
CREATE TABLE nation_elo_ratings (
    nation_name text NOT NULL,
    nation_elo_k5 integer,
    nation_elo_k10 integer,
    nation_elo_k20 integer,
    nation_elo_k30 integer,
    nation_elo_k40 integer,
    nation_elo_k80 integer
);
CREATE TABLE odds (
    id integer NOT NULL,
    match_id integer NOT NULL,
    bookmaker_id integer NOT NULL,
    bookmaker_name text NOT NULL,
    bet_type_id integer NOT NULL,
    bet_type_name text NOT NULL,
    bet_value text NOT NULL,
    odds_value numeric(10,2) NOT NULL,
    retrieved_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    api_last_updated timestamp without time zone
);
CREATE SEQUENCE odds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE odds_id_seq OWNED BY odds.id;
CREATE TABLE processed_info (
    match_id bigint NOT NULL,
    is_processed boolean DEFAULT false,
    with_formation boolean DEFAULT false,
    processed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    processing_mode character varying(20) DEFAULT 'training'::character varying
);
CREATE TABLE stage_of_season_future (
    match_id integer,
    start_time timestamp without time zone,
    season_start_date timestamp without time zone,
    season_end_date timestamp without time zone,
    stage_of_season real,
    stage_of_season_category text
);
CREATE TABLE stage_of_season_history (
    match_id integer,
    start_time timestamp without time zone,
    season_start_date timestamp without time zone,
    season_end_date timestamp without time zone,
    stage_of_season real,
    stage_of_season_category text
);
CREATE TABLE teammatchhistory (
    team_id integer NOT NULL,
    match_id integer NOT NULL,
    start_time timestamp without time zone,
    competition_season_name text,
    competition_id text,
    competition_name text,
    competition_country text,
    goals_scored integer,
    goals_conceded integer,
    result character varying(4),
    is_home integer,
    is_intraleague_match integer,
    is_domestic_cup_match integer,
    is_continental_cup_match integer
);
CREATE TABLE teams_mapping (
    team_id integer NOT NULL,
    team_name character varying(255) NOT NULL,
    domestic_country character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE ONLY h2h_stats ALTER COLUMN team_pair_id SET DEFAULT nextval('h2h_stats_team_pair_id_seq'::regclass);
ALTER TABLE ONLY odds ALTER COLUMN id SET DEFAULT nextval('odds_id_seq'::regclass);
ALTER TABLE ONLY club_elo_ratings
    ADD CONSTRAINT club_elo_ratings_pkey PRIMARY KEY (team_id);
ALTER TABLE ONLY continent_elo_ratings
    ADD CONSTRAINT continent_elo_ratings_pkey PRIMARY KEY (continent_name);
ALTER TABLE ONLY counter_table
    ADD CONSTRAINT counter_table_pkey PRIMARY KEY (competition_id);
ALTER TABLE ONLY form_future
    ADD CONSTRAINT form_future_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY form_history
    ADD CONSTRAINT form_history_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY form_matches_cache
    ADD CONSTRAINT form_matches_cache_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY h2h_future
    ADD CONSTRAINT h2h_future_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY h2h_history
    ADD CONSTRAINT h2h_history_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY h2h_stats
    ADD CONSTRAINT h2h_stats_pkey PRIMARY KEY (team_pair_id);
ALTER TABLE ONLY h2h_stats
    ADD CONSTRAINT h2h_stats_team1_id_team2_id_key UNIQUE (team1_id, team2_id);
ALTER TABLE ONLY league_elo_ratings
    ADD CONSTRAINT league_elo_ratings_pkey PRIMARY KEY (league_id);
ALTER TABLE ONLY leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (id);
ALTER TABLE ONLY match_info_future
    ADD CONSTRAINT match_info_future_pkey PRIMARY KEY (match_id, competition_id);
ALTER TABLE ONLY match_info_history
    ADD CONSTRAINT match_info_history_pkey PRIMARY KEY (match_id, competition_id);
ALTER TABLE ONLY match_result_predictions
    ADD CONSTRAINT match_result_predictions_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY nation_elo_ratings
    ADD CONSTRAINT nation_elo_ratings_pkey PRIMARY KEY (nation_name);
ALTER TABLE ONLY odds
    ADD CONSTRAINT odds_pkey PRIMARY KEY (id);
ALTER TABLE ONLY processed_info
    ADD CONSTRAINT processed_info_pkey PRIMARY KEY (match_id);
ALTER TABLE ONLY teammatchhistory
    ADD CONSTRAINT teammatchhistory_pkey PRIMARY KEY (team_id, match_id);
ALTER TABLE ONLY teams_mapping
    ADD CONSTRAINT teams_mapping_pkey PRIMARY KEY (team_id);
CREATE INDEX idx_elo_future_start_time ON elo_future USING btree (start_time);
CREATE INDEX idx_form_matches_away_team ON form_matches_cache USING btree (away_team_id);
CREATE INDEX idx_form_matches_home_team ON form_matches_cache USING btree (home_team_id);
CREATE INDEX idx_formation_future_start_time ON formation_future USING btree (start_time);
CREATE INDEX idx_h2h_stats_team_pair ON h2h_stats USING btree (team1_id, team2_id);
CREATE INDEX idx_league_standings_future_start_time ON league_standings_future USING btree (start_time);
CREATE INDEX idx_match_info_future_start_time ON match_info_future USING btree (start_time);
CREATE INDEX idx_matches_away_team_id ON matches USING btree (away_team_id);
CREATE INDEX idx_matches_competition_season_away ON matches USING btree (competition_id, competition_season_name, away_team_id);
CREATE INDEX idx_matches_competition_season_home ON matches USING btree (competition_id, competition_season_name, home_team_id);
CREATE INDEX idx_matches_completed_for_training ON matches USING btree (start_time, match_id) WHERE ((home_score IS NOT NULL) AND (away_score IS NOT NULL));
CREATE INDEX idx_matches_home_team_id ON matches USING btree (home_team_id);
CREATE INDEX idx_matches_not_started ON matches USING btree (match_status, start_time) WHERE (match_status = 'NS'::text);
CREATE INDEX idx_matches_ns_teams ON matches USING btree (match_status, start_time, home_team_name, away_team_name) WHERE (match_status = 'NS'::text);
CREATE INDEX idx_odds_match_id ON odds USING btree (match_id);
CREATE INDEX idx_odds_retrieved_at ON odds USING btree (retrieved_at);
CREATE INDEX idx_processed_info_training_done ON processed_info USING btree (match_id) WHERE ((is_processed = true) AND ((processing_mode)::text = 'training'::text));
CREATE INDEX idx_stage_of_season_future_start_time ON stage_of_season_future USING btree (start_time);
CREATE INDEX idx_team_name ON teams_mapping USING btree (team_name);
CREATE INDEX idx_team_name_lower ON teams_mapping USING btree (lower((team_name)::text));
ALTER TABLE ONLY processed_info
    ADD CONSTRAINT processed_info_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(match_id);
"""


def upgrade() -> None:
    for statement in _schema_statements(BASELINE_SCHEMA_SQL):
        op.execute(statement)


def downgrade() -> None:
    op.drop_table("teams_mapping")
    op.drop_table("teammatchhistory")
    op.drop_table("stage_of_season_history")
    op.drop_table("stage_of_season_future")
    op.drop_table("processed_info")
    op.drop_table("odds")
    op.drop_table("nation_elo_ratings")
    op.drop_table("matches")
    op.drop_table("match_result_predictions")
    op.drop_table("match_info_history")
    op.drop_table("match_info_future")
    op.drop_table("leagues")
    op.drop_table("league_standings_future")
    op.drop_table("league_elo_ratings")
    op.drop_table("h2h_stats")
    op.drop_table("h2h_history")
    op.drop_table("h2h_future")
    op.drop_table("formation_history")
    op.drop_table("formation_future")
    op.drop_table("form_matches_cache")
    op.drop_table("form_history")
    op.drop_table("form_future")
    op.drop_table("elo_history")
    op.drop_table("elo_future")
    op.drop_table("counter_table")
    op.drop_table("continent_elo_ratings")
    op.drop_table("club_elo_ratings")


def _schema_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";\n") if statement.strip()]
