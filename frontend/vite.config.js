import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,  // 监听所有网络接口
    allowedHosts: [
      'skiuo.supanx.net',
      'localhost',
      '.supanx.net'  // 允许所有 supanx.net 子域名
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
})
