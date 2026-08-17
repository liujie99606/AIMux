import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const configPath = resolve(projectRoot, 'config', 'runtime-ports.json');

const rawConfig = JSON.parse(readFileSync(configPath, 'utf8'));
const mode = process.argv[2] ?? 'stable';
const value = process.argv[3] ?? 'backend';
const runtime = rawConfig[mode];

if (!runtime || !['backend', 'frontend'].includes(value)) {
  console.error(`无效的端口配置查询：模式=${mode}，类型=${value}`);
  process.exit(1);
}

const port = Number(runtime[value]);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  console.error(`端口配置无效：${mode}.${value}`);
  process.exit(1);
}

process.stdout.write(String(port));
