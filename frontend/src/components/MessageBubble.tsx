import React from "react";
import { Box, Typography } from "@mui/material";
import { Message } from "../types/types";

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
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
      <Typography>{message.text}</Typography>
    </Box>
  );
};

export default MessageBubble;
