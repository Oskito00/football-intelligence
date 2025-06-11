"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";

interface Prediction {
  match_id: number;
  predicted_result: number;
  start_time: string;
  home_team_name: string;
  away_team_name: string;
  prob_home_win: number;
  prob_draw: number;
  prob_away_win: number;
}

export default function MatchPredictions() {
  console.log("MatchPredictions component starting to render");

  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filteredMatches = React.useMemo(() => {
    if (!predictions || predictions.length === 0) {
      return [];
    }

    return predictions.filter((match) => {
      if (!match?.home_team_name || !match?.away_team_name) {
        return false;
      }

      if (!searchTerm) return true;

      return (
        match.home_team_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        match.away_team_name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    });
  }, [predictions, searchTerm]);

  const sortedMatches = filteredMatches.sort((a, b) => {
    return new Date(a.start_time).getTime() - new Date(b.start_time).getTime();
  });

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch("/api/analysis");

        if (!response.ok) {
          throw new Error("Failed to fetch data");
        }

        const data = await response.json();

        // Debug logs
        console.log("=== API RESPONSE DEBUG ===");
        console.log("Data type:", typeof data);
        console.log("Is array:", Array.isArray(data));
        console.log("Data length:", data?.length);
        console.log("First 3 items:", data?.slice(0, 3));

        // Check each item for problematic data
        if (Array.isArray(data)) {
          data.forEach((item, index) => {
            if (!item?.home_team_name || !item?.away_team_name) {
              console.log(`Problematic item at index ${index}:`, item);
            }
            if (typeof item?.home_team_name !== "string") {
              console.log(
                `home_team_name not string at index ${index}:`,
                typeof item?.home_team_name,
                item?.home_team_name
              );
            }
            if (typeof item?.away_team_name !== "string") {
              console.log(
                `away_team_name not string at index ${index}:`,
                typeof item?.away_team_name,
                item?.away_team_name
              );
            }
          });
        }
        console.log("=== END DEBUG ===");

        setPredictions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    }

    fetchData();
  }, []);

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

  const getResultText = (predictedResult: number) => {
    switch (predictedResult) {
      case 0:
        return "Away Win";
      case 1:
        return "Draw";
      case 2:
        return "Home Win";
      default:
        return "Unknown";
    }
  };

  return (
    <div className="min-h-screen bg-green-100 text-black">
      <header className="w-full bg--700 text-white py-4">
        <div className="flex justify-start">
          <Image
            src="/INBETMENTS (1).png"
            alt="InBETments Logo"
            width={200}
            height={80}
            priority
            className="h-[40px] sm:h-[50px] md:h-[65px] lg:h-[65px] w-[100px] sm:w-[125px] md:w-[150px] lg:w-[162px]"
          />
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 my-12">
        <h1 className="text-3xl font-bold text-center text-green-700 mb-4">
          Football Match Predictions
        </h1>
        <p className="mt-2 text-lg text-center text-gray-600">
          AI-powered predictions for upcoming football matches
        </p>

        <div className="mt-8 mb-12 flex justify-center">
          <input
            type="text"
            className="w-full max-w-lg p-3 rounded-full border border-gray-300"
            placeholder="Search for teams..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 py-4">
          {sortedMatches.map((match, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-center mb-6">
                <h2 className="text-lg font-semibold text-green-700 mb-2">
                  {match.home_team_name || "Unknown Team"} vs{" "}
                  {match.away_team_name || "Unknown Team"}
                </h2>
                <p className="text-sm text-gray-600">
                  {match.start_time
                    ? new Date(match.start_time).toLocaleString()
                    : "TBD"}
                </p>
              </div>

              <div className="mb-4">
                <p className="text-sm font-semibold mb-2 text-center">
                  Match Outcome Probabilities
                </p>
                <div className="relative h-8 bg-gray-200 rounded overflow-hidden">
                  {/* Home Win (Red) */}
                  <div
                    className="absolute left-0 h-full bg-red-500 flex items-center justify-center text-xs text-white font-bold"
                    style={{ width: `${(match.prob_home_win || 0) * 100}%` }}
                  >
                    {(match.prob_home_win || 0) * 100 >= 15 &&
                      `${((match.prob_home_win || 0) * 100).toFixed(0)}%`}
                  </div>
                  {/* Draw (Gray) */}
                  <div
                    className="absolute h-full bg-gray-500 flex items-center justify-center text-xs text-white font-bold"
                    style={{
                      left: `${(match.prob_home_win || 0) * 100}%`,
                      width: `${(match.prob_draw || 0) * 100}%`,
                    }}
                  >
                    {(match.prob_draw || 0) * 100 >= 15 &&
                      `${((match.prob_draw || 0) * 100).toFixed(0)}%`}
                  </div>
                  {/* Away Win (Blue) */}
                  <div
                    className="absolute h-full bg-blue-500 flex items-center justify-center text-xs text-white font-bold"
                    style={{
                      left: `${
                        ((match.prob_home_win || 0) + (match.prob_draw || 0)) *
                        100
                      }%`,
                      width: `${(match.prob_away_win || 0) * 100}%`,
                    }}
                  >
                    {(match.prob_away_win || 0) * 100 >= 15 &&
                      `${((match.prob_away_win || 0) * 100).toFixed(0)}%`}
                  </div>
                </div>

                {/* Legend below the bar */}
                <div className="flex justify-between text-xs text-gray-600 mt-2">
                  <span>
                    🏠 Home Win: {((match.prob_home_win || 0) * 100).toFixed(1)}
                    %
                  </span>
                  <span>
                    🤝 Draw: {((match.prob_draw || 0) * 100).toFixed(1)}%
                  </span>
                  <span>
                    ✈️ Away Win: {((match.prob_away_win || 0) * 100).toFixed(1)}
                    %
                  </span>
                </div>
              </div>

              <div className="text-center pt-4 border-t border-gray-200">
                <p className="text-sm text-gray-600">Most likely outcome:</p>
                <p className="text-lg font-bold text-green-700">
                  {getResultText(match.predicted_result)}
                </p>
              </div>
            </div>
          ))}
        </div>

        {sortedMatches.length === 0 && (
          <div className="text-center py-12">
            <p className="text-lg text-gray-600">
              {searchTerm
                ? "No matches found for your search."
                : "No upcoming matches found."}
            </p>
          </div>
        )}
      </div>

      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-green-700 mb-6 text-center">
            How to Read the Predictions
          </h2>
          <div className="space-y-4 text-gray-700 text-lg">
            <p>
              Our AI model analyzes team performance, historical data, and other
              factors to predict match outcomes:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <span className="font-semibold text-red-600">Red bar:</span>{" "}
                Home team win probability
              </li>
              <li>
                <span className="font-semibold text-gray-600">Gray bar:</span>{" "}
                Draw probability
              </li>
              <li>
                <span className="font-semibold text-blue-600">Blue bar:</span>{" "}
                Away team win probability
              </li>
            </ul>
            <p className="mt-4">
              The longer the bar, the higher the probability for that outcome.
              The &quot;Most likely outcome&quot; shows what our model predicts
              will happen.
            </p>
            <p className="text-sm text-gray-600 mt-6 italic">
              Note: These are predictions based on data analysis and should not
              be used as the sole basis for any decisions.
            </p>
          </div>
        </div>
      </div>

      <footer className="bg-green-700 text-white py-6 mt-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <h3 className="text-lg font-bold">InBETments</h3>
              <p className="text-sm">AI-powered match outcome predictions</p>
            </div>
            <div className="text-center md:text-right">
              <p className="text-sm">© 2025 InBETments. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}