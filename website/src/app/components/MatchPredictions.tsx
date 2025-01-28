"use client";

import React, { useState, useEffect } from "react";

interface Prediction {
  start_time: string;
  home_team: string;
  away_team: string;
  predicted_outcome: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  model_type: string;
  home_bookie_prob: number;
  draw_bookie_prob: number;
  away_bookie_prob: number;
  home_value: number;
  draw_value: number;
  away_value: number;
  home_kelly: number;
  draw_kelly: number;
  away_kelly: number;
}

interface PredictionAnalysis {
  // Add appropriate properties for PredictionAnalysis
}

export default function MatchPredictions() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        // Just fetch the prediction analysis data since it has everything we need
        const response = await fetch("/api/analysis");

        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }

        const data = await response.json();
        setPredictions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, []);

  const filteredMatches = predictions.filter(
    (match) =>
      match.home_team.toLowerCase().includes(searchTerm.toLowerCase()) ||
      match.away_team.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-green-100 flex items-center justify-center">
        <p className="text-xl text-green-800">Loading predictions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-green-100 flex items-center justify-center">
        <p className="text-xl text-red-600">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-green-100 text-black">
      <header className="w-full bg--700 text-white py-4">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-start">
            <img
              src="/INBETMENTS (1).png"
              alt="InBETments Logo"
              className="h-[80px] sm:h-[100px] md:h-[120px] lg:h-[130px]"
            />
          </div>
        </div>
      </header>

      <div className="bg-black text-white py-2 overflow-hidden">
        <div className="animate-ticker whitespace-nowrap">
          {[...Array(1)].map((_, i) => (
            <span key={i}>
              {predictions
                .flatMap((match) => [
                  ...(match.home_value > 5
                    ? [
                        {
                          teams: `${match.home_team} vs ${match.away_team}`,
                          bet: "Home Win",
                          value: match.home_value,
                          kelly: match.home_kelly,
                          isSafe: match.predicted_outcome === "Home Win",
                        },
                      ]
                    : []),
                  ...(match.draw_value > 5
                    ? [
                        {
                          teams: `${match.home_team} vs ${match.away_team}`,
                          bet: "Draw",
                          value: match.draw_value,
                          kelly: match.draw_kelly,
                          isSafe: match.predicted_outcome === "Draw",
                        },
                      ]
                    : []),
                  ...(match.away_value > 5
                    ? [
                        {
                          teams: `${match.home_team} vs ${match.away_team}`,
                          bet: "Away Win",
                          value: match.away_value,
                          kelly: match.away_kelly,
                          isSafe: match.predicted_outcome === "Away Win",
                        },
                      ]
                    : []),
                ])
                .sort((a, b) => b.value - a.value)
                .map((bet, index) => (
                  <span
                    key={`${i}-${index}`}
                    className={`inline-block mx-4 ${
                      bet.isSafe ? "text-green-400" : "text-yellow-400"
                    }`}
                  >
                    {bet.isSafe ? "✅ More secure bet: " : "⚠️ Riskier bet: "}
                    {bet.teams} • {bet.bet}: +{bet.value.toFixed(1)}% value (Bet{" "}
                    {bet.kelly.toFixed(1)}% of pot)
                    <span className="mx-4">|</span>
                  </span>
                ))}
            </span>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 my-12">
        <p className="mt-2 text-lg text-center text-gray-600">
          Search for a game to see the predictions.
        </p>
        <div className="mt-4 mb-12 flex justify-center">
          <input
            type="text"
            className="w-full max-w-lg p-3 rounded-full border border-gray-300"
            placeholder="Search here..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 py-4">
          {filteredMatches.map((match, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow-md p-4 overflow-hidden"
            >
              <div className="text-center mb-4">
                <h2 className="text-lg font-semibold text-green-700 truncate">
                  {match.home_team} vs {match.away_team}
                </h2>
                <p className="text-sm text-gray-600">
                  {new Date(match.start_time).toLocaleString()}
                </p>
              </div>

              <p className="text-sm font-semibold mb-1">
                Our Model Probabilities:
              </p>
              <div className="h-4 w-full flex items-center relative group mb-4">
                <div
                  className="h-4 bg-red-500 relative hover:opacity-80"
                  style={{ width: `${match.home_win_prob * 100}%` }}
                  title={`Home Win: ${(match.home_win_prob * 100).toFixed(1)}%`}
                ></div>
                <div
                  className="h-4 bg-gray-400 relative hover:opacity-80"
                  style={{ width: `${match.draw_prob * 100}%` }}
                  title={`Draw: ${(match.draw_prob * 100).toFixed(1)}%`}
                ></div>
                <div
                  className="h-4 bg-blue-500 relative hover:opacity-80"
                  style={{ width: `${match.away_win_prob * 100}%` }}
                  title={`Away Win: ${(match.away_win_prob * 100).toFixed(1)}%`}
                ></div>
              </div>

              <p className="text-sm font-semibold mb-1">
                Bookmaker Probabilities:
              </p>
              <div className="h-4 w-full flex items-center relative group mb-4">
                <div
                  className="h-4 bg-red-300 relative hover:opacity-80"
                  style={{
                    width: `${
                      (match.home_bookie_prob /
                        (match.home_bookie_prob +
                          match.draw_bookie_prob +
                          match.away_bookie_prob)) *
                      100
                    }%`,
                  }}
                  title={`Home Win: ${(match.home_bookie_prob * 100).toFixed(
                    1
                  )}%`}
                ></div>
                <div
                  className="h-4 bg-gray-300 relative hover:opacity-80"
                  style={{
                    width: `${
                      (match.draw_bookie_prob /
                        (match.home_bookie_prob +
                          match.draw_bookie_prob +
                          match.away_bookie_prob)) *
                      100
                    }%`,
                  }}
                  title={`Draw: ${(match.draw_bookie_prob * 100).toFixed(1)}%`}
                ></div>
                <div
                  className="h-4 bg-blue-300 relative hover:opacity-80"
                  style={{
                    width: `${
                      (match.away_bookie_prob /
                        (match.home_bookie_prob +
                          match.draw_bookie_prob +
                          match.away_bookie_prob)) *
                      100
                    }%`,
                  }}
                  title={`Away Win: ${(match.away_bookie_prob * 100).toFixed(
                    1
                  )}%`}
                ></div>
              </div>

              <div className="mt-4">
                <p className="text-sm font-semibold mb-2">Value bets:</p>
                <div className="space-y-1">
                  {match.home_value > 0 && (
                    <p
                      className={`text-sm ${
                        match.predicted_outcome === "Home Win"
                          ? "text-green-600"
                          : "text-yellow-600"
                      }`}
                    >
                      Home Win: +{match.home_value.toFixed(1)}% value (Bet{" "}
                      {match.home_kelly.toFixed(1)}% of your pot)
                    </p>
                  )}
                  {match.draw_value > 0 && (
                    <p
                      className={`text-sm ${
                        match.predicted_outcome === "Draw"
                          ? "text-green-600"
                          : "text-yellow-600"
                      }`}
                    >
                      Draw: +{match.draw_value.toFixed(1)}% value (Bet{" "}
                      {match.draw_kelly.toFixed(1)}% of your pot)
                    </p>
                  )}
                  {match.away_value > 0 && (
                    <p
                      className={`text-sm ${
                        match.predicted_outcome === "Away Win"
                          ? "text-green-600"
                          : "text-yellow-600"
                      }`}
                    >
                      Away Win: +{match.away_value.toFixed(1)}% value (Bet{" "}
                      {match.away_kelly.toFixed(1)}% of your pot)
                    </p>
                  )}
                </div>
              </div>

              <p className="text-sm text-center mt-4 text-gray-500">
                Predicted Outcome: {match.predicted_outcome}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
