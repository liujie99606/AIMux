import { defineStore } from 'pinia';
export const useAppStore = defineStore('app', {
  state: () => ({ version: '0.1.0', now: new Date() }),
  actions: {
    startClock() {
      setInterval(() => (this.now = new Date()), 1000);
    },
  },
});
