// Inert stand-in for the `server-only` package under test (aliased in
// vitest.config.ts). The real package exists purely to THROW when a module graph
// destined for the browser imports it — which is exactly what we want in the app
// and exactly what we must neutralize to unit-test those same server modules.
export {};
