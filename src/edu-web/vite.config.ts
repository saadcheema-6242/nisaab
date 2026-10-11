import { resolve } from 'node:path'
import { defineConfig } from 'vitest/config'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [viteReact(), tailwindcss()],
  envDir: '../../',
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  test: {
    // streamdown pulls in KaTeX's stylesheet; let Vite transform it so tests
    // can render the chat's markdown the way the app does
    server: { deps: { inline: ['streamdown'] } },
  },
})
