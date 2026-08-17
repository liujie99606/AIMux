import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

type RuntimeMode = 'stable' | 'development';

type RuntimePorts = Record<RuntimeMode, { backend: number; frontend: number }>;

const runtimeMode: RuntimeMode =
  process.env.AIMUX_RUNTIME_MODE === 'development' ? 'development' : 'stable';
const runtimePorts = JSON.parse(
  readFileSync(resolve(process.cwd(), 'config', 'runtime-ports.json'), 'utf8'),
) as RuntimePorts;

export default defineConfig({
  plugins: [vue()],
  clearScreen: false,
  server: { port: runtimePorts[runtimeMode].frontend, strictPort: true },
});
