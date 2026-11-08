import type { NextConfig } from "next";

// Cache Components / partial prefetching are off: every screen renders live,
// per-run backend state fetched in the browser through the server-side proxy.
const nextConfig: NextConfig = {
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
