/// <reference types="vitest/config"/>
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { playwright } from "@vitest/browser-playwright";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    projects: [
      {
        extends: true,
        test: {
          include: ["tests/**/*.unit.{test,spec}.ts"],
          name: "unit",
          environment: "node",
        },
      },
      {
        extends: true,
        test: {
          include: ["tests/**/*.browser.{test,spec}.ts"],
          name: "browser",
          browser: {
            enabled: true,
            provider: playwright(),
            instances: [{ browser: "chromium" }],
          },
        },
      },
    ],
  },
});
