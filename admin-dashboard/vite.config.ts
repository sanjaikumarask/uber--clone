import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/dashboard/",
  server: {
    port: 5174,       // 👈 ADMIN PORT
    strictPort: true,
  },
});
