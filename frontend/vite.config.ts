import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Build straight into the backend package so FastAPI serves it (backend/app/ui)
    outDir: path.resolve(__dirname, '../backend/app/ui'),
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/repository': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/v2': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
