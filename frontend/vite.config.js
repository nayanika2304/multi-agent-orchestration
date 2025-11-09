import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Detect if running in Docker (check for host.docker.internal or use environment variable)
const isDocker = process.env.DOCKER === 'true' || process.env.HOSTNAME?.includes('docker')
const orchestratorHost = isDocker ? 'host.docker.internal' : '127.0.0.1'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Listen on all interfaces (needed for Docker)
    proxy: {
      '/api': {
        target: `http://${orchestratorHost}:8000`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/management/api')
      }
    }
  }
})

