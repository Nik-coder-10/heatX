import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    host: '0.0.0.0', // Required for Docker
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true, // Better hot reload in Docker
    },
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },

  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          map: ['leaflet'],
          charts: ['echarts', 'echarts-for-react'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
});