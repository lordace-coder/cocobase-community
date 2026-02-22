/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				coco: {
					50: '#f0f4ff',
					100: '#e0e9ff',
					200: '#c7d7fe',
					300: '#a5bbfc',
					400: '#8196f8',
					500: '#6272f3',
					600: '#4d52e8',
					700: '#3f42ce',
					800: '#3438a7',
					900: '#2f3585',
					950: '#1c1f52'
				}
			}
		}
	},
	plugins: []
};
