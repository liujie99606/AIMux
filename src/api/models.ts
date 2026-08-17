import { del, get, post, put } from './client';
export type CatalogModel = {
  id: string;
  name: string;
  type: 'openai' | 'anthropic';
  is_default: number;
};
export const modelsApi = {
  list: (type?: string) =>
    get<{ items: CatalogModel[] }>(`/api/models${type ? `?type=${type}` : ''}`),
  create: (v: unknown) => post<CatalogModel>('/api/models', v),
  update: (id: string, v: unknown) => put<CatalogModel>(`/api/models/${id}`, v),
  remove: (id: string) => del<void>(`/api/models/${id}`),
  setDefault: (id: string) => post<CatalogModel>(`/api/models/${id}/set-default`),
};
