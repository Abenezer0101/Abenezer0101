import type { Research } from "./types";

// In-memory, per-server-instance. Survives requests, not deploys. That is the
// right trade for a demo: no database, no eviction policy, no stale-data bugs
// that outlive a restart.
const store = new Map<string, Research>();

// Module state is per lambda instance in serverless; a global pin keeps the
// cache alive across hot reloads in dev too.
const g = globalThis as unknown as { __aiCache?: Map<string, Research> };
export const cache: Map<string, Research> = g.__aiCache ?? (g.__aiCache = store);
