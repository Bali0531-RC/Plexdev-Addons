/// <reference types="vite/client" />

declare const __BUILD_TIME__: string;

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_DISCORD_CLIENT_ID: string
  readonly VITE_STRIPE_PUBLISHABLE_KEY: string
  readonly VITE_PAYPAL_CLIENT_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
