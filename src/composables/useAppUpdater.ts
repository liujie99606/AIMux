import { computed, ref, shallowRef } from 'vue';
import { check, type Update } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

const RELEASE_PAGE_URL = 'https://github.com/quietforge-dev/AIMux/releases/latest';

const errorMessage = (error: unknown) => (error instanceof Error ? error.message : String(error));

export const useAppUpdater = () => {
  const visible = ref(false);
  const checking = ref(false);
  const installing = ref(false);
  const progressPercentage = ref<number | undefined>();
  const progressLabel = ref('正在下载更新包...');
  const update = shallowRef<Update | null>(null);

  const version = computed(() => update.value?.version ?? '');
  const notes = computed(() => update.value?.body ?? '');

  const checkForUpdates = async () => {
    if (checking.value || installing.value) return;
    checking.value = true;
    try {
      const result = await check({ timeout: 15_000 });
      if (!result) return { available: false as const };
      if (update.value) await update.value.close();
      update.value = result;
      visible.value = true;
      return { available: true as const };
    } finally {
      checking.value = false;
    }
  };

  const installAndRelaunch = async () => {
    const candidate = update.value;
    if (!candidate || installing.value) return;
    installing.value = true;
    progressPercentage.value = undefined;
    progressLabel.value = '正在下载更新包...';
    let downloadedBytes = 0;
    let contentLength = 0;
    try {
      await candidate.downloadAndInstall((event) => {
        if (event.event === 'Started') {
          contentLength = event.data.contentLength ?? 0;
          progressLabel.value = '正在下载更新包...';
          return;
        }
        if (event.event === 'Progress') {
          downloadedBytes += event.data.chunkLength;
          if (contentLength > 0) {
            progressPercentage.value = Math.min(
              100,
              Math.round((downloadedBytes / contentLength) * 100),
            );
          }
          return;
        }
        progressPercentage.value = 100;
        progressLabel.value = '正在安装更新，即将重启...';
      });
      await candidate.close();
      await relaunch();
    } catch (error) {
      throw new Error(`更新安装失败：${errorMessage(error)}`);
    } finally {
      installing.value = false;
    }
  };

  const releasePageUrl = () => RELEASE_PAGE_URL;

  return {
    checking,
    installAndRelaunch,
    installing,
    notes,
    progressLabel,
    progressPercentage,
    releasePageUrl,
    checkForUpdates,
    version,
    visible,
  };
};
