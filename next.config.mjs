// On Vercel, /api/* is served by the Python function in api/index.py (see vercel.json).
// Locally, `next dev` doesn't run it, so point API_ORIGIN at a running copy of the API:
//   uvicorn api.index:app --port 8000
//   API_ORIGIN=http://127.0.0.1:8000 npm run dev
const apiOrigin = process.env.API_ORIGIN;

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return apiOrigin ? [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }] : [];
  },
};

export default nextConfig;
