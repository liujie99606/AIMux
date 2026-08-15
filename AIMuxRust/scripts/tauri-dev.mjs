import { spawn } from 'node:child_process';

const projectRoot = process.cwd();

const isWindows = process.platform === 'win32';
const command = isWindows ? (process.env.ComSpec ?? 'cmd.exe') : 'npm';
const args = isWindows ? ['/d', '/s', '/c', 'npm run tauri dev'] : ['run', 'tauri', 'dev'];
const child = spawn(command, args, {
  cwd: projectRoot,
  env: {
    ...process.env,
    AIMUX_PORT: '7790',
    AIMUX_MONITORING_ENABLED: 'false',
    VITE_API_BASE: 'http://127.0.0.1:7790',
  },
  stdio: 'inherit',
});

child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
