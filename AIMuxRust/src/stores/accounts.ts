import { defineStore } from 'pinia';
import { accountsApi, type Account } from '../api/accounts';
export const useAccountsStore = defineStore('accounts', {
  state: () => ({ items: [] as Account[], total: 0, loading: false }),
  actions: {
    async load() {
      this.loading = true;
      try {
        const data = await accountsApi.list('?limit=200');
        this.items = data.items;
        this.total = data.total;
      } finally {
        this.loading = false;
      }
    },
  },
});
