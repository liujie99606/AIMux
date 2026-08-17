import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import './styles/index.scss';
import router from './router';
import App from './App.vue';
import { invoke } from '@tauri-apps/api/core';
import { setApiBase } from './api/client';

const configureTauriGateway = async (): Promise<boolean> => {
  try {
    setApiBase(await invoke<string>('gateway_url'));
    return true;
  } catch {
    // 浏览器直接运行前端时，继续使用 VITE_API_BASE 或默认 7789 端口。
    return false;
  }
};

const bindDevtoolsShortcut = () => {
  window.addEventListener('keydown', (event) => {
    const isDevtoolsShortcut = event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key === 'I');
    if (!isDevtoolsShortcut) return;
    event.preventDefault();
    invoke('open_devtools').catch(() => undefined);
  });
};

const bootstrap = async () => {
  if (await configureTauriGateway()) bindDevtoolsShortcut();
  createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app');
};

void bootstrap();
