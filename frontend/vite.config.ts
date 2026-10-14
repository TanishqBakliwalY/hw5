import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// `npm run dev` serves the desk at http://localhost:5173 and opens it in the browser.
// The page calls the FastAPI backend at http://localhost:8000 (see src/api.ts / VITE_API_BASE),
// which allows this origin through CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    open: true,
  },
})
