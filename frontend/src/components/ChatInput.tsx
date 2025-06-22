import React from "react";
import { TextField, InputAdornment, IconButton, Stack } from "@mui/material";
import { Send, Stop, FastForward } from "@mui/icons-material";

interface ChatInputProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSend: () => void;
  onStop?: () => void;
  onFastForward?: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
  isTyping?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onStop,
  onFastForward,
  onKeyPress,
  isTyping = false,
}) => {
  return (
    <TextField
      fullWidth
      value={value}
      onChange={onChange}
      onKeyPress={onKeyPress}
      placeholder="message..."
      variant="outlined"
      size="small"
      sx={{
        "& .MuiOutlinedInput-root": {
          backgroundColor: "#f8f8f8",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          color: "#424242",
          "&:hover": {
            backgroundColor: "#ffffff",
          },
          "&.Mui-focused": {
            backgroundColor: "#ffffff",
          },
        },
        "& .MuiOutlinedInput-notchedOutline": {
          borderColor: "transparent",
        },
        "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
          borderColor: "transparent",
        },
        "& .MuiInputBase-input::placeholder": {
          color: "#757575",
          opacity: 0.8,
        },
      }}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <Stack direction="row" spacing={0.5}>
              {isTyping ? (
                <>
                  <IconButton
                    onClick={onStop}
                    color="inherit"
                    size="small"
                    sx={{
                      transition: "transform 0.3s ease-in-out",
                      transform: "scale(0.9)",
                      color: "grey.500",
                    }}
                  >
                    <Stop />
                  </IconButton>
                  <IconButton
                    onClick={onFastForward}
                    color="inherit"
                    size="small"
                    sx={{
                      transition: "transform 0.3s ease-in-out",
                      transform: "scale(0.9)",
                      color: "grey.500",
                    }}
                  >
                    <FastForward />
                  </IconButton>
                </>
              ) : (
                <IconButton
                  onClick={onSend}
                  color="primary"
                  size="small"
                  sx={{
                    transition: "transform 0.3s ease-in-out",
                    transform: "scale(1)",
                  }}
                >
                  <Send />
                </IconButton>
              )}
            </Stack>
          </InputAdornment>
        ),
      }}
    />
  );
};

export default ChatInput;
 