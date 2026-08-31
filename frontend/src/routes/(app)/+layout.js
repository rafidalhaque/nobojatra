// Authenticated area: never prerendered, never server-rendered — pure CSR so
// there is zero pre-auth content anywhere in the build output (spec 11.1).
export const ssr = false;
export const prerender = false;
