export default {
    testDir: "./e2e",
    reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
    use: {
      browserName: "chromium",
      channel: "chrome",
      headless: true,
      baseURL: "http://localhost:5173",
    },
  };