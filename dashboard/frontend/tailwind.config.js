/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16', // Deep Space Blue-Black
        surface: '#131b2e', // Deep Navy-Slate
        primary: '#6366f1', // Vibrant Violet-Indigo
        accent: '#f43f5e', // Electric Coral-Rose
        text: '#f8fafc', // Off-white
        muted: '#64748b', // Cool Gray
      }
    },
  },
  plugins: [],
}
