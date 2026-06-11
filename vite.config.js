import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname, 'src/frontend'),
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/frontend/index.html'),
        app: resolve(__dirname, 'src/frontend/app.html'),
        auth: resolve(__dirname, 'src/frontend/auth.html'),
        feedback: resolve(__dirname, 'src/frontend/feedback.html'),
        feedback_admin: resolve(__dirname, 'src/frontend/feedback_admin.html')
      }
    }
  }
});

