import { defineStore } from 'pinia';
import { invoke } from '@tauri-apps/api/core';

export const useAppStore = defineStore('app', {
  state: () => ({ version: import.meta.env.VITE_APP_VERSION, now: new Date() }),
  actions: {
    startClock() {
      setInterval(() => (this.now = new Date()), 1000);
    },
    async loadVersion() {
      try {
        const version = await invoke<string>('app_version');
        if (version) this.version = version;
      } catch {
        // 浏览器开发模式没有 Tauri command，使用 Vite 注入的 package 版本。
      }
    },
  },
});
