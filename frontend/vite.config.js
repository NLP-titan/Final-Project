import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, requests to /api are proxied to VITE_API_PROXY_TARGET
// (default: http://localhost:8000). In a production build the frontend should
// hit a same-origin /api or an absolute URL set via VITE_API_BASE_URL.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
  return {
    plugins: [react()],
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      proxy: {
        '/api': { target, changeOrigin: true },
      },
    },
  }
})
