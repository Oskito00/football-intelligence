import { createTheme } from "@mui/material";

const createCustomTheme = (mode: "light" | "dark") =>
  createTheme({
    palette: {
      mode,
      primary: {
        main: "#2e7d32", // Forest green
        light: "#4caf50",
        dark: "#1b5e20",
      },
      background: {
        default: mode === "dark" ? "#2B3228" : "#f0f0f0",
        paper: mode === "dark" ? "#2B3228" : "#ffffff",
      },
      grey: {
        300: "#e0e0e0",
        400: "#bdbdbd",
        500: "#9e9e9e",
        600: "#757575",
        700: "#616161",
        800: "#595959", // Darker grey for user messages
      },
      custom: {
        headerBar: "#88a374",
      },
    },
    components: {
      MuiTextField: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-root": {
              borderRadius: 25,
              height: 45,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: "#CFCFC4",
            color: "#000000",
          },
        },
      },
    },
  });

// Add custom palette types
declare module "@mui/material/styles" {
  interface Palette {
    custom: {
      headerBar: string;
    };
  }
  interface PaletteOptions {
    custom?: {
      headerBar: string;
    };
  }
}

export default createCustomTheme;
