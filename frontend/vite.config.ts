import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/static/',
  // Backend credentials must never enter the frontend build.
  envDir: false,
  publicDir: false,
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], clearMocks: true },
});
