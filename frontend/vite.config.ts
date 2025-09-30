import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: 'http://django:8000',
        changeOrigin: true,
        secure: false,
      },
      // Restrict to API subpaths only to avoid hijacking SPA routes on reload
      '/shifts/api': {
        target: 'http://django:8000',
        changeOrigin: true,
        secure: false,
      },
      '/orchestrators/api': {
        target: 'http://django:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
