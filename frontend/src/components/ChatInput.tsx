import React from "react";
import { TextField, InputAdornment, IconButton } from "@mui/material";
import { Send } from "@mui/icons-material";

interface ChatInputProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSend: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onKeyPress,
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
            <IconButton onClick={onSend} color="primary" size="small">
              <Send />
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
};

export default ChatInput;
