/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { optimizeCss: true },
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

module.exports = nextConfig;
