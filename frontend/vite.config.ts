import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  const prodUrl = env.VITE_FRONTEND_PUBLIC_URL_PROD
  const allowedHosts = prodUrl ? [new URL(prodUrl).hostname] : []

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      allowedHosts
    },
    preview: {
      allowedHosts
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-vue': ['vue', 'vue-router', 'pinia'],
            'vendor-katex': ['katex'],
            'vendor-markdown': ['marked', 'dompurify'],
            'vendor-hljs': ['highlight.js/lib/core'],
          }
        }
      }
    }
  }
})
