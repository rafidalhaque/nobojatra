import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // No SSR server. Prerender the static routes at build time; every dynamic
    // (authenticated) route is served by the SPA fallback and rendered client-side.
    adapter: adapter({ fallback: 'index.html', precompress: true, strict: false }),
    alias: { $lib: 'src/lib' }
  }
};

export default config;
