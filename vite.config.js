import { defineConfig } from 'vite';

export default defineConfig({
  root: 'src/frontend',
  server: {
    port: 5173,
    proxy: {
      '/fetch-financial-data': 'http://localhost:8000',
      '/trade/decision': 'http://localhost:8000'
    }
  },
  build: {
    outDir: '../../dist',
    emptyOutDir: true
  }
});
