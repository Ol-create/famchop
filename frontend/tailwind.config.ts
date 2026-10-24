import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#E8590C", // Jollof Orange
        secondary: "#2B8A3E", // Leaf Green
        accent: "#F59F00", // Palm Oil Yellow
        cocoa: "#3D2C29", // main text
        cream: "#FFF8F0", // page background
        surface: "#FFFFFF",
        muted: "#8C7B75", // Warm Grey
        danger: "#C92A2A", // Pepper Red
      },
      fontFamily: {
        heading: ["var(--font-poppins)", "sans-serif"],
        sans: ["var(--font-inter)", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
