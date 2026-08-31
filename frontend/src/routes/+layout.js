// No SSR server anywhere. Static routes are prerendered at build; everything
// else is served by the SPA fallback (see svelte.config.js).
export const prerender = true;
export const csr = true;
export const trailingSlash = 'never';
