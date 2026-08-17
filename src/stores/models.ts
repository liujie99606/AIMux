import { defineStore } from 'pinia';
import { modelsApi, type CatalogModel } from '../api/models';
export const useModelsStore = defineStore('models', {
  state: () => ({ items: [] as CatalogModel[], loading: false }),
  getters: {
    byType: (state) => (type: string) => state.items.filter((item) => item.type === type),
  },
  actions: {
    async load() {
      this.loading = true;
      try {
        this.items = (await modelsApi.list()).items;
      } finally {
        this.loading = false;
      }
    },
  },
});
