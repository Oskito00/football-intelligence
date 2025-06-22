import React, { useState, useRef, useEffect } from "react";
import {
  AppBar,
  Box,
  Container,
  IconButton,
  Paper,
  Toolbar,
  ThemeProvider,
  CssBaseline,
} from "@mui/material";
import { Brightness4, Brightness7 } from "@mui/icons-material";
import { ColorMode, Message } from "./types/types";
import createCustomTheme from "./theme/theme";
import MessageBubble from "./components/MessageBubble";
import ChatInput from "./components/ChatInput";
import WelcomeMessage from "./components/WelcomeMessage";
import TypewriterMessage from "./components/TypewriterMessage";

const API_URL = process.env.REACT_APP_API_URL || "https://inbetments-c9b27c044fce.herokuapp.com/";

function App() {
  const [mode, setMode] = useState<ColorMode>("dark");
  const [messages, setMessages] = useState<Message[]>([]);
  const [typingMessage, setTypingMessage] = useState<Message | null>(null);
  const [input, setInput] = useState("");
  const [typingTimeoutId, setTypingTimeoutId] = useState<NodeJS.Timeout | null>(
    null
  );
  const theme = createCustomTheme(mode);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chatContainer = chatContainerRef.current;
    if (!chatContainer) return;

    // Create a MutationObserver to watch for content changes
    const observer = new MutationObserver(() => {
      chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: "smooth",
      });
    });

    // Start observing the chat container for changes
    observer.observe(chatContainer, {
      childList: true, // Watch for changes to child elements
      subtree: true, // Watch all descendants, not just direct children
      characterData: true, // Watch for text content changes
    });

    return () => observer.disconnect();
  }, []); // Empty dependency array since we only want to set this up once

  const handleStopTyping = () => {
    if (typingTimeoutId) {
      clearTimeout(typingTimeoutId);
      setTypingTimeoutId(null);
    }
    if (typingMessage) {
      // Add the partial message to the messages array
      setMessages((prev) => [...prev, typingMessage]);
      setTypingMessage(null);
    }
  };

  const handleFastForward = () => {
    if (typingTimeoutId) {
      clearTimeout(typingTimeoutId);
      setTypingTimeoutId(null);
    }
    if (typingMessage) {
      // Add the complete message immediately
      setMessages((prev) => [...prev, typingMessage]);
      setTypingMessage(null);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Add user message
    const newMessages = [...messages, { text: input, isBot: false }];
    setMessages(newMessages);
    setInput("");

    try {
      // Make API call to backend
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: input }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response from server");
      }

      const data = await response.json();
      const botResponse = {
        text: data.response,
        isBot: true,
      };

      // Start bot response with typewriter
      setTypingMessage(botResponse);

      // After typing is complete, add to regular messages
      const timeoutId = setTimeout(() => {
        setMessages((prev) => [...prev, botResponse]);
        setTypingMessage(null);
        setTypingTimeoutId(null);
      }, 1000 + botResponse.text.length * 30); // Approximate typing time

      setTypingTimeoutId(timeoutId);
    } catch (error) {
      console.error("Error:", error);
      const errorResponse = {
        text: "Sorry, I encountered an error processing your request. Please try again.",
        isBot: true,
      };
      setMessages((prev) => [...prev, errorResponse]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (typingMessage) {
        handleStopTyping();
      } else {
        handleSendMessage();
      }
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          flexGrow: 1,
          height: "100vh",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.default",
        }}
      >
        <AppBar position="static" color="primary">
          <Toolbar>
            <Box
              component="img"
              src="/inbetments.png"
              alt="Inbetments Logo"
              sx={{
                height: 40,
                mr: 2,
                objectFit: "contain",
              }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <IconButton
              color="inherit"
              onClick={() => setMode(mode === "light" ? "dark" : "light")}
            >
              {mode === "light" ? <Brightness4 /> : <Brightness7 />}
            </IconButton>
          </Toolbar>
        </AppBar>

        <Container
          maxWidth="md"
          sx={{
            flexGrow: 1,
            py: 2,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            pb: 8,
            width: "100%",
            maxWidth: "900px !important",
          }}
        >
          <Paper
            ref={chatContainerRef}
            sx={{
              flexGrow: 1,
              p: 2,
              mb: 2,
              overflow: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 1,
              bgcolor: "background.default",
              boxShadow: "none",
              "&::-webkit-scrollbar": {
                width: "8px",
              },
              "&::-webkit-scrollbar-track": {
                background: "transparent",
              },
              "&::-webkit-scrollbar-thumb": {
                background: "rgba(255, 255, 255, 0.1)",
                borderRadius: "4px",
              },
              "&::-webkit-scrollbar-thumb:hover": {
                background: "rgba(255, 255, 255, 0.2)",
              },
            }}
          >
            <Box sx={{ flexGrow: 1 }}>
              {messages.length === 0 ? (
                <WelcomeMessage />
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {messages.map((message, index) => (
                    <MessageBubble key={index} message={message} />
                  ))}
                  {typingMessage && (
                    <TypewriterMessage
                      messages={[typingMessage]}
                      sx={{
                        fontSize: { xs: "0.95rem", sm: "1rem" },
                      }}
                    />
                  )}
                </Box>
              )}
            </Box>
          </Paper>

          <ChatInput
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onSend={handleSendMessage}
            onStop={handleStopTyping}
            onFastForward={handleFastForward}
            onKeyPress={handleKeyPress}
            isTyping={!!typingMessage}
          />
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
