import { get, put } from './client';
export type Settings = {
  host: string;
  port: number;
  db_path: string;
  upstream_timeout_seconds: number;
  first_token_timeout_seconds: number;
  request_retry_attempts: number;
  upstream_proxy_enabled: boolean;
  upstream_proxy_url: string;
  monitoring_enabled: boolean;
  local_token: string;
  launch_at_login: boolean;
};
export const settingsApi = {
  get: () => get<Settings>('/api/settings'),
  update: (v: Settings) => put<Settings>('/api/settings', v),
};
