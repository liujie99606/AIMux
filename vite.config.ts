import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

type RuntimeMode = 'stable' | 'development';

type RuntimePorts = Record<RuntimeMode, { backend: number; frontend: number }>;
type PackageMetadata = { version: string };

const runtimeMode: RuntimeMode =
  process.env.AIMUX_RUNTIME_MODE === 'development' ? 'development' : 'stable';
const runtimePorts = JSON.parse(
  readFileSync(resolve(process.cwd(), 'config', 'runtime-ports.json'), 'utf8'),
) as RuntimePorts;
const packageMetadata = JSON.parse(
  readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'),
) as PackageMetadata;

export default defineConfig({
  plugins: [vue()],
  clearScreen: false,
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(packageMetadata.version),
  },
  server: { port: runtimePorts[runtimeMode].frontend, strictPort: true },
});
