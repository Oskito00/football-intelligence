import React, { useEffect, useState, useRef } from "react";
import { Box, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import { Message } from "../types/types";

const blink = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`;

interface TypewriterMessageProps {
  messages: Message[];
  onComplete?: () => void;
  className?: string;
  sx?: any;
}

interface MessageState {
  text: string;
  isComplete: boolean;
}

const TypewriterMessage: React.FC<TypewriterMessageProps> = ({
  messages,
  onComplete,
  className,
  sx = {},
}) => {
  const [messageIndex, setMessageIndex] = useState(0);
  const [messageStates, setMessageStates] = useState<MessageState[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll to the bottom whenever text changes
  useEffect(() => {
    if (containerRef.current) {
      // Find the closest scrollable parent
      let scrollParent = containerRef.current.parentElement;
      while (
        scrollParent &&
        getComputedStyle(scrollParent).overflow === "visible"
      ) {
        scrollParent = scrollParent.parentElement;
      }

      if (scrollParent) {
        scrollParent.scrollTop = scrollParent.scrollHeight;
      }
    }
  }, [messageStates]); // This will trigger on every text update

  useEffect(() => {
    if (!messages || messages.length === 0) return;

    if (messageIndex >= messages.length) {
      onComplete?.();
      return;
    }

    // Initialize message states if not already done
    if (messageStates.length < messageIndex + 1) {
      setMessageStates((prev) => [...prev, { text: "", isComplete: false }]);
      return;
    }

    const currentMessage = messages[messageIndex];
    if (!currentMessage) return;

    const currentState = messageStates[messageIndex];
    if (!currentState) return;

    if (!currentState.isComplete) {
      if (currentState.text.length < currentMessage.text.length) {
        const timer = setTimeout(() => {
          setMessageStates((prev) => {
            const newStates = [...prev];
            newStates[messageIndex] = {
              text: currentMessage.text.slice(0, currentState.text.length + 1),
              isComplete: false,
            };
            return newStates;
          });
        }, 30);
        return () => clearTimeout(timer);
      } else {
        const timer = setTimeout(() => {
          setMessageStates((prev) => {
            const newStates = [...prev];
            newStates[messageIndex].isComplete = true;
            return newStates;
          });
          setMessageIndex((i) => i + 1);
        }, 800);
        return () => clearTimeout(timer);
      }
    }
  }, [messageIndex, messages, messageStates, onComplete]);

  const renderMessage = (
    message: Message,
    typedText: string | null = null,
    isTyping: boolean = false
  ) => {
    if (!message) return null;

    return (
      <Box
        sx={{
          alignSelf: message.isBot ? "flex-start" : "flex-end",
          backgroundColor: message.isBot ? "transparent" : "grey.800",
          color: message.isBot ? "text.primary" : "white",
          p: message.isBot ? 0 : 1.5,
          px: message.isBot ? 0 : 2,
          borderRadius: message.isBot ? 0 : "20px",
          maxWidth: "70%",
        }}
      >
        <Typography
          className={className}
          sx={{
            whiteSpace: "pre-line",
            color: "inherit",
            ...sx,
            "&::after": isTyping
              ? {
                  content: '"|"',
                  position: "relative",
                  marginLeft: "2px",
                  animation: `${blink} 1s step-end infinite`,
                }
              : {},
          }}
        >
          {typedText ?? message.text}
        </Typography>
      </Box>
    );
  };

  if (!messages || messages.length === 0) return null;

  return (
    <Box
      ref={containerRef}
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      {messageStates.map((state, i) => {
        const message = messages[i];
        if (!message) return null;

        return renderMessage(
          message,
          state.text,
          !state.isComplete && i === messageIndex
        );
      })}
    </Box>
  );
};

export default TypewriterMessage;
