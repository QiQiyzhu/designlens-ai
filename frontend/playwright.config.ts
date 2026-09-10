import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: "../outputs/browser-report.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5175",
    viewport: { width: 1440, height: 1024 },
    channel: process.platform === "win32" ? "msedge" : undefined,
    trace: "off",
    screenshot: "only-on-failure",
    actionTimeout: 10000,
  },
  webServer: [
    {
      command:
        process.platform === "win32"
          ? '"..\\.venv\\Scripts\\python.exe" "..\\scripts\\browser_server.py"'
          : "python ../scripts/browser_server.py",
      url: "http://127.0.0.1:8002/api/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5175",
      env: { DESIGNLENS_API_TARGET: "http://127.0.0.1:8002" },
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
