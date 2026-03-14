import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // Proxy para novos endpoints da API v1
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // Mantém endpoints legados para compatibilidade
      '/search': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/analytics': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
