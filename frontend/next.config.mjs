/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true
  },
  // Ensure ESM packages from TanStack are transpiled correctly
  transpilePackages: [
    '@tanstack/react-table',
    '@tanstack/table-core'
  ]
};

export default nextConfig;
