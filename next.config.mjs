/** @type {import('next').NextConfig} */
// /api/* is served by the Python function in api/index.py (see vercel.json).
// Plain `next dev` doesn't run it — use `vercel dev` so the API is proxied.
const nextConfig = {};

export default nextConfig;
