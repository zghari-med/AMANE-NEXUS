export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#EFF4FF',
          100: '#E9E3FF',
          200: '#C4B5FD',
          300: '#A78BFA',
          400: '#7C3AED',
          500: '#7551FF',
          600: '#422AFB',
          700: '#3311DB',
          800: '#190793',
          900: '#02044A',
        },
        navy: {
          50:  '#d0dcfb',
          100: '#aac0fe',
          200: '#a3b9f8',
          300: '#728fea',
          400: '#3652ba',
          500: '#1b3bbb',
          600: '#24388a',
          700: '#1B2559',
          800: '#111c44',
          900: '#0b1437',
        },
        secondaryGray: {
          100: '#E0E5F2',
          200: '#E1E9F8',
          300: '#F4F7FE',
          400: '#E9EDF7',
          500: '#8F9BBA',
          600: '#A3AED0',
          700: '#707EAE',
          800: '#4A5568',
          900: '#1B2559',
        },
      },
      backgroundImage: {
        'gradient-brand':      'linear-gradient(135deg, #868CFF 0%, #4318FF 100%)',
        'gradient-navy':       'linear-gradient(135deg, #1B2559 0%, #0b1437 100%)',
        'gradient-secondary':  'linear-gradient(135deg, #3b82f6 0%, #1e40af 100%)',
        'gradient-primary':    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'horizon': '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
        'horizon-sm': '0px 18px 40px rgba(112, 144, 176, 0.12)',
      },
      letterSpacing: {
        tight: '-0.5px',
      },
    },
  },
  plugins: [],
}
