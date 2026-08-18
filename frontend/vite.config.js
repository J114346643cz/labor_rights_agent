import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 开发代理：把 /api 开头的请求转发给后端 FastAPI（默认 8000 端口）
    // 好处：前端与后端同源，无需处理 CORS；SSE 流式响应也能原样透传
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
