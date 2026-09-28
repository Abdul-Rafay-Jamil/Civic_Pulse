/**
 * Runtime configuration — loaded from /config.js at container start.
 * This is the build-once-deploy-many solution: the API URL is NOT baked
 * into the Vite build. Instead, nginx generates /config.js from env vars
 * at container startup.
 *
 * For local development, the Vite proxy handles /api → backend.
 */

interface AppConfig {
  API_BASE_URL: string;
}

declare global {
  interface Window {
    __CIVICPULSE_CONFIG__?: AppConfig;
  }
}

export function getConfig(): AppConfig {
  // Runtime config from /config.js (production)
  if (window.__CIVICPULSE_CONFIG__) {
    return window.__CIVICPULSE_CONFIG__;
  }
  // Fallback for development — Vite proxy handles /api
  return {
    API_BASE_URL: '',
  };
}

export const config = getConfig();
