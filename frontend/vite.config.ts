import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const apiBaseUrl = loadEnv(mode, process.cwd(), 'VITE_').VITE_API_BASE_URL?.trim()
  if (command === 'build' && !apiBaseUrl) {
    throw new Error('VITE_API_BASE_URL must be set for frontend builds')
  }

  return {
    plugins: [react()],
  }
})
