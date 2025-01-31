"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

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

interface PerformanceData {
  date: string;
  pot_value: number;
}

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function MatchPredictions() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);

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

  useEffect(() => {
    async function fetchPerformanceData() {
      try {
        const response = await fetch("/api/performance");
        const data = await response.json();
        setPerformanceData(data);
      } catch (error) {
        console.error("Error fetching performance data:", error);
      }
    }

    fetchPerformanceData();
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
        <div className="container mx-auto px-4 sm:px-6 lg:px-8"></div>
      </header>

      <div className="bg-black text-white py-2 overflow-hidden">
        <div className="ticker-wrapper">
          <div className="ticker-content">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
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
                      {bet.teams}: Bet{" "}
                      <span className="font-bold">{bet.kelly.toFixed(1)}%</span>{" "}
                      of your pot on a{" "}
                      <span className="font-bold">{bet.bet}</span>
                      <span className="mx-4">|</span>
                    </span>
                  ))}
              </div>
            ))}
          </div>
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
              <div className="relative h-6 bg-gray-200 rounded overflow-hidden">
                {/* Home Win (Red) */}
                <div
                  className="absolute left-0 h-full bg-red-500 flex items-center justify-center text-xs text-white font-bold"
                  style={{ width: `${match.home_win_prob * 100}%` }}
                >
                  {(match.home_win_prob * 100).toFixed(0)}%
                </div>
                {/* Draw (Gray) */}
                <div
                  className="absolute h-full bg-gray-500 flex items-center justify-center text-xs text-white font-bold"
                  style={{
                    left: `${match.home_win_prob * 100}%`,
                    width: `${match.draw_prob * 100}%`,
                  }}
                >
                  {(match.draw_prob * 100).toFixed(0)}%
                </div>
                {/* Away Win (Blue) */}
                <div
                  className="absolute h-full bg-blue-500 flex items-center justify-center text-xs text-white font-bold"
                  style={{
                    left: `${(match.home_win_prob + match.draw_prob) * 100}%`,
                    width: `${match.away_win_prob * 100}%`,
                  }}
                >
                  {(match.away_win_prob * 100).toFixed(0)}%
                </div>
              </div>

              <p className="text-sm font-semibold mb-1">
                Bookmaker Probabilities:
              </p>
              <div className="relative h-6 bg-gray-200 rounded overflow-hidden">
                {(() => {
                  // Calculate total to normalize
                  const total =
                    match.home_bookie_prob +
                    match.draw_bookie_prob +
                    match.away_bookie_prob;

                  // Normalize each probability
                  const normalizedHome = match.home_bookie_prob / total;
                  const normalizedDraw = match.draw_bookie_prob / total;
                  const normalizedAway = match.away_bookie_prob / total;

                  return (
                    <>
                      <div
                        className="absolute left-0 h-full bg-red-300 flex items-center justify-center text-xs text-white font-bold"
                        style={{ width: `${normalizedHome * 100}%` }}
                      >
                        {(normalizedHome * 100).toFixed(0)}%
                      </div>
                      <div
                        className="absolute h-full bg-gray-400 flex items-center justify-center text-xs text-white font-bold"
                        style={{
                          left: `${normalizedHome * 100}%`,
                          width: `${normalizedDraw * 100}%`,
                        }}
                      >
                        {(normalizedDraw * 100).toFixed(0)}%
                      </div>
                      <div
                        className="absolute h-full bg-blue-300 flex items-center justify-center text-xs text-white font-bold"
                        style={{
                          left: `${(normalizedHome + normalizedDraw) * 100}%`,
                          width: `${normalizedAway * 100}%`,
                        }}
                      >
                        {(normalizedAway * 100).toFixed(0)}%
                      </div>
                    </>
                  );
                })()}
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
                      {match.predicted_outcome === "Home Win" ? "✅" : "⚠️"}{" "}
                      <span className="font-bold">Home Win</span>: +
                      {match.home_value.toFixed(1)}% value (Bet{" "}
                      <span className="font-bold">
                        {match.home_kelly.toFixed(1)}%
                      </span>{" "}
                      of your pot)
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
                      {match.predicted_outcome === "Draw" ? "✅" : "⚠️"}{" "}
                      <span className="font-bold">Draw</span>: +
                      {match.draw_value.toFixed(1)}% value (Bet{" "}
                      <span className="font-bold">
                        {match.draw_kelly.toFixed(1)}%
                      </span>{" "}
                      of your pot)
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
                      {match.predicted_outcome === "Away Win" ? "✅" : "⚠️"}{" "}
                      <span className="font-bold">Away Win</span>: +
                      {match.away_value.toFixed(1)}% value (Bet{" "}
                      <span className="font-bold">
                        {match.away_kelly.toFixed(1)}%
                      </span>{" "}
                      of your pot)
                    </p>
                  )}
                </div>
              </div>

              <p className="text-sm text-center mt-4 text-gray-500">
                <span className="font-bold">
                  Most likely outcome: {match.predicted_outcome}
                </span>
              </p>
            </div>
          ))}
        </div>
        <div className="container mx-auto px-4 mb-6">
          <div className="flex flex-col space-y-4">
            <div className="flex flex-col sm:flex-row justify-center sm:space-x-8 space-y-2 sm:space-y-0 text-sm">
              <div className="flex items-center text-green-600 justify-center">
                <span className="mr-2">✅</span>
                <span>
                  More secure bet (betting on the most likely outcome)
                </span>
              </div>
              <div className="flex items-center text-yellow-600 justify-center">
                <span className="mr-2">⚠️</span>
                <span>Riskier bet (betting on a less likely outcome)</span>
              </div>
            </div>
            <div className="text-sm text-center text-gray-600">
              For the most accurate predictions please wait until 45 minutes
              before the match starts so that the model can consider the team
              lineups
            </div>
          </div>
        </div>
      </div>
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-bold text-green-700 mb-6 text-center">
            How to Use inBETments
          </h2>
          <div className="space-y-4 text-gray-700 text-lg">
            <p>
              Our AI-powered platform helps you make smarter betting decisions.
              Here&apos;s how to use it:
            </p>
            <ol className="list-decimal pl-6 space-y-4">
              <li>
                <span className="font-semibold">
                  Check the Probability Bars:
                </span>
                <ul className="list-disc pl-6 mt-2 space-y-1">
                  <li>Red bar shows home win probability</li>
                  <li>Gray bar shows draw probability</li>
                  <li>Blue bar shows away win probability</li>
                </ul>
              </li>
              <li>
                <span className="font-semibold">
                  Compare with Bookmaker Odds:
                </span>
                <br />
                Our model compares the probabilities of the bookmakers and our
                model to find value bets. Note: We take an average of the odds
                across lots of bookmakers so please make sure to check your
                bookmakers odds before betting and see if they align with the
                odds on our website.
              </li>
              <li>
                <span className="font-semibold">Look for Value Bets:</span>
                <br />
                Green indicators show safer bets that align with our predicted
                outcome. Yellow indicators show riskier bets that still offer
                good value.
                <p className="mt-4">
                  Higher value percentages indicate bigger discrepancies between
                  our model and bookmaker odds, potentially offering better
                  betting opportunities.
                </p>
              </li>
              <li>
                <span className="font-semibold">How much to bet:</span>
                <br />
                The suggested bet size is calculated using a formula that
                optimizes long-term growth.
                <p className="font-semibold mt-6">
                  Remember: The percentages we suggest you should bet are
                  maximum amounts - you can always bet less.
                </p>
              </li>
            </ol>
          </div>
        </div>
        <div className="max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl font-bold text-green-700 mb-6 text-center">
            Does it Work?
          </h2>
          <div className="space-y-4 text-gray-700 text-lg">
            <p>
              Track our performance over time. This graph shows our betting pot
              growth since we started using this model:
            </p>
            <div className="w-full h-[400px] bg-white p-4 rounded-lg shadow-lg">
              <Line
                data={{
                  labels: performanceData.map((d) => d.date),
                  datasets: [
                    {
                      label: "Betting Pot Value (£)",
                      data: performanceData.map((d) => d.pot_value),
                      borderColor: "rgb(34, 197, 94)",
                      backgroundColor: "rgba(34, 197, 94, 0.1)",
                      tension: 0.1,
                      fill: true,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: "top",
                    },
                    title: {
                      display: true,
                      text: "Performance Over Time",
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                    },
                  },
                }}
              />
            </div>
            <p className="mt-4">
              Be sure to check back regularly to see how we are doing.
            </p>
          </div>
        </div>
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-green-700 mb-6 text-center">
            Bet Responsibly
          </h2>
          <div className="space-y-4 text-gray-700 text-lg">
            <p>
              At inBETments, we&apos;re committed to promoting responsible
              betting practices. While our AI-driven predictions aim to make
              betting smarter, it&apos;s crucial to remember that no bet is ever
              guaranteed. The algorithm makes its predictions based on what it
              thinks will be the most likely outcome but due to the
              unpredictable nature of sports, it is not always right.
            </p>
            <p>We encourage you to:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Only bet what you can afford to lose</li>
              <li>Set strict betting limits and stick to them</li>
            </ul>
          </div>
        </div>
      </div>
      <footer className="bg-green-700 text-white py-6 mt-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <h3 className="text-lg font-bold">inBETments</h3>
              <p className="text-sm">Making betting smarter</p>
            </div>
            <div className="text-center md:text-right">
              <p className="text-sm">© 2025 inBETments. All rights reserved.</p>
              <p className="text-sm mt-1">
                Only bet what you can afford to lose
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}