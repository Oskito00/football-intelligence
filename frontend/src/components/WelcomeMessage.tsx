import React from "react";
import { Box } from "@mui/material";
import TypewriterMessage from "./TypewriterMessage";
import { Message } from "../types/types";

interface WelcomeMessageProps {
  onComplete?: () => void;
}

const WelcomeMessage: React.FC<WelcomeMessageProps> = ({ onComplete }) => {
  // Combine all messages into a single sequence
  const allMessages: Message[] = [
    { text: "Hi, 👋", isBot: true },
    { text: "I am an AI football pundit", isBot: true },
    {
      text: "I can help you with predictions, analysis, and insights across all major leagues.",
      isBot: true,
    },
    { text: "Here are some examples of what you can ask me...", isBot: true },
    {
      text: "What's your prediction for the upcoming Manchester United vs Liverpool match?",
      isBot: false,
    },
    {
      text: "Based on recent form and historical data, I predict Liverpool to win 2-1. Liverpool's pressing game has been exceptional, winning 75% of their away matches this season, while United have struggled defensively at home.",
      isBot: true,
    },
    { text: "Show me Arsenal's recent form", isBot: false },
    {
      text: "Arsenal's last 5 matches:\n✅ Arsenal 3-1 Spurs\n✅ Arsenal 2-0 Brighton\n⚪ Newcastle 0-0 Arsenal\n✅ Arsenal 2-1 Wolves\n❌ Villa 1-0 Arsenal\n\nThey're currently in strong form with 10 points from their last 5 games.",
      isBot: true,
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <TypewriterMessage
        messages={allMessages}
        onComplete={onComplete}
        sx={{
          fontSize: { xs: "0.95rem", sm: "1rem" },
        }}
      />
    </Box>
  );
};

export default WelcomeMessage;
