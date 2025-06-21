import React from "react";
import { Box, useTheme, useMediaQuery } from "@mui/material";
import { keyframes } from "@mui/system";

interface CategoryBubblesProps {
  onCategoryClick: (category: string) => void;
}

const rotate = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(-360deg); }
`;

const categories = [
  {
    label: "Match Predictions",
    example: "What's your prediction for Manchester United vs Liverpool?",
  },
  {
    label: "Player Analysis",
    example: "How has Erling Haaland performed this season?",
  },
  { label: "Team Statistics", example: "Show me Arsenal's recent form" },
  { label: "League Insights", example: "Who's likely to finish in the top 4?" },
  {
    label: "Historical Data",
    example: "What's the head-to-head record between Chelsea and Spurs?",
  },
];

const CategoryBubbles: React.FC<CategoryBubblesProps> = ({
  onCategoryClick,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const size = isMobile ? 280 : 400;
  const radius = size / 2;
  const padding = 60;
  const totalSize = size + padding * 2;
  const allCategories = categories.map((c) => c.label).join("  •  ");

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: isMobile ? "360px" : "480px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* Rotating circle text */}
      <Box
        sx={{
          width: totalSize,
          height: totalSize,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          animation: `${rotate} 40s linear infinite`,
        }}
      >
        <svg
          width={totalSize}
          height={totalSize}
          viewBox={`0 0 ${totalSize} ${totalSize}`}
        >
          <defs>
            <path
              id="circlePath"
              d={`
                M ${totalSize / 2},${totalSize / 2} 
                m -${radius},0 
                a ${radius},${radius} 0 1,1 ${size},0 
                a ${radius},${radius} 0 1,1 -${size},0
              `}
              fill="none"
            />
          </defs>

          <text
            fill={theme.palette.grey[400]}
            fontSize={isMobile ? "16px" : "24px"}
            letterSpacing="3"
            style={{
              transition: "all 0.3s ease",
              fontWeight: 500,
            }}
          >
            <textPath href="#circlePath" startOffset="0%">
              {allCategories}
            </textPath>
          </text>

          {/* Clickable areas */}
          {categories.map((category, index) => {
            const angle = (index * 360) / categories.length;
            const rad = (angle * Math.PI) / 180;
            const x = totalSize / 2 + radius * Math.cos(rad);
            const y = totalSize / 2 + radius * Math.sin(rad);

            return (
              <circle
                key={category.label}
                cx={x}
                cy={y}
                r={40}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onClick={() => onCategoryClick(category.example)}
              />
            );
          })}
        </svg>
      </Box>
    </Box>
  );
};

export default CategoryBubbles;
