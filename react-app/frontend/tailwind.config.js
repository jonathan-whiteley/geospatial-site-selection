/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Panda Express brand colors
        // Class names retain `orange` keys to avoid touching every component;
        // the hex values are Panda Red. `brand-gold` is the accent.
        brand: {
          orange: '#C8102E',
          'orange-dark': '#9F0C24',
          'orange-light': '#E8344E',
          red: '#C8102E',
          'red-dark': '#9F0C24',
          'red-light': '#E8344E',
          gold: '#FFC72C',
          'gold-dark': '#E0AC1F',
          'gold-light': '#FFD75A',
        },
        // Map layer colors
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
        // Professional chart colors
        chart: {
          1: '#3b82f6',
          2: '#10b981',
          3: '#8b5cf6',
          4: '#f59e0b',
          5: '#06b6d4',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-out-right': 'slideOutRight 0.3s ease-out',
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-out-left': 'slideOutLeft 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
        'accordion-down': 'accordionDown 0.2s ease-out',
        'accordion-up': 'accordionUp 0.2s ease-out',
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
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideOutLeft: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-100%)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        accordionDown: {
          '0%': { height: '0' },
          '100%': { height: 'var(--radix-accordion-content-height)' },
        },
        accordionUp: {
          '0%': { height: 'var(--radix-accordion-content-height)' },
          '100%': { height: '0' },
        },
      },
      boxShadow: {
        'glass': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
        'glass-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}
