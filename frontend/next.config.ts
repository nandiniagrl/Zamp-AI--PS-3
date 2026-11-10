import type { NextConfig } from "next";

// Cache Components / partial prefetching are off: every screen renders live,
// per-run backend state fetched in the browser through the server-side proxy.
const nextConfig: NextConfig = {
  // Phase 14: self-contained server (.next/standalone/server.js) for the Cloud Run image.
  output: "standalone",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
