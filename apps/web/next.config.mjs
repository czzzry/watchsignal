import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const appDir = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.0.23"],
  turbopack: {
    root: join(appDir, "../.."),
  },
};

export default nextConfig;
