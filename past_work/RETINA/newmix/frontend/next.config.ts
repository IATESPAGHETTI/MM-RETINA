import type { NextConfig } from "next";

// Set PRESENTATION_ONLY=1 (and NEXT_PUBLIC_PRESENTATION_ONLY=1) on the host to
// publish just the /presentation deck: every other route redirects to it.
const presentationOnly = process.env.PRESENTATION_ONLY === "1";

const nextConfig: NextConfig = {
  async redirects() {
    if (!presentationOnly) return [];
    return [
      { source: "/", destination: "/presentation", permanent: false },
      {
        source: "/:path((?!presentation|_next|samples|favicon.ico).+)",
        destination: "/presentation",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
