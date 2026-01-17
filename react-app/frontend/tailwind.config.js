/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors from original app
        brand: {
          orange: '#F06B38',
          'orange-dark': '#d85f30',
        },
        // Map legend colors
        map: {
          stores: '#10b981',
          'stores-dark': '#065f46',
          candidates: '#ef4444',
          'candidates-dark': '#dc2626',
          convenience: '#3b82f6',
          'convenience-dark': '#1e3a8a',
          competitors: '#a855f7',
          'competitors-dark': '#9333ea',
          partner: {
            bg: '#DBEAFE',
            border: '#3B82F6',
            text: '#1E3A8A',
          },
          'new-store': {
            bg: '#FEF3C7',
            border: '#F59E0B',
            text: '#92400E',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-out-right': 'slideOutRight 0.3s ease-out',
      },
      keyframes: {
        slideInRight: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideOutRight: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
    },
  },
  plugins: [],
}
