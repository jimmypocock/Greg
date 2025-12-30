import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    resolveAlias: {
      // Force ESM versions to avoid CJS/ESM mixing issues with Turbopack
      'yjs': 'yjs/dist/yjs.mjs',
      'y-websocket': 'y-websocket/src/y-websocket.js',
    },
  },
};

export default nextConfig;
