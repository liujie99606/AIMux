<template>
  <el-container class="shell">
    <el-aside width="214px" class="sidebar">
      <div class="brand"><span class="brand-mark">A</span><span>AIMux</span></div>
      <el-menu :default-active="route.path" router class="nav">
        <el-menu-item index="/accounts"
          ><el-icon><User /></el-icon>账号管理</el-menu-item
        >
        <el-menu-item index="/models"
          ><el-icon><Grid /></el-icon>模型维护</el-menu-item
        >
        <el-menu-item index="/usage"
          ><el-icon><Tickets /></el-icon>使用记录</el-menu-item
        >
        <el-menu-item index="/statistics"
          ><el-icon><DataAnalysis /></el-icon>数据统计</el-menu-item
        >
        <el-menu-item index="/monitor"
          ><el-icon><Monitor /></el-icon>监控管理</el-menu-item
        >
        <el-menu-item index="/settings"
          ><el-icon><Setting /></el-icon>设置</el-menu-item
        >
      </el-menu>
      <div class="sidebar-foot">
        <div>{{ clock }}</div>
        <div class="sidebar-actions">
          <el-button text class="sidebar-action" @click="openGithub">
            <el-icon><Link /></el-icon>GitHub
          </el-button>
          <el-button text class="sidebar-action" @click="checkForUpdates">
            <el-icon><Refresh /></el-icon>检查更新
          </el-button>
        </div>
        <div class="version">v{{ app.version }}</div>
      </div>
    </el-aside>
    <el-main class="main"><router-view /></el-main>
  </el-container>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { invoke } from '@tauri-apps/api/core';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  DataAnalysis,
  Grid,
  Link,
  Monitor,
  Refresh,
  Setting,
  Tickets,
  User,
} from '@element-plus/icons-vue';
import { useAppStore } from '../stores/app';
const route = useRoute();
const app = useAppStore();
onMounted(() => app.startClock());
const clock = computed(() => app.now.toLocaleTimeString('zh-CN', { hour12: false }));

const GITHUB_URL = 'https://github.com/quietforge-dev/AIMux';
const RELEASE_API = 'https://api.github.com/repos/quietforge-dev/AIMux/releases/latest';

const openExternal = async (url: string) => {
  try {
    await invoke('open_external_url', { url });
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
};

const openGithub = async () => {
  await ElMessageBox.alert(`将使用默认浏览器打开：\n${GITHUB_URL}`, '打开 GitHub', {
    confirmButtonText: '打开',
  });
  await openExternal(GITHUB_URL);
};

const versionKey = (value: string) =>
  value
    .replace(/^v/i, '')
    .split('.')
    .slice(0, 3)
    .map((part) => Number.parseInt(part, 10) || 0);

const isNewer = (latest: string, current: string) => {
  const left = versionKey(latest);
  const right = versionKey(current);
  for (const index of [0, 1, 2]) {
    if (left[index] !== right[index]) return left[index] > right[index];
  }
  return false;
};

const checkForUpdates = async () => {
  try {
    const response = await fetch(RELEASE_API, {
      headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'AIMux' },
    });
    if (!response.ok) {
      if (response.status === 403) throw new Error('GitHub API 请求过于频繁，请稍后再试');
      throw new Error(`GitHub 返回 HTTP ${response.status}`);
    }
    const release = (await response.json()) as { tag_name?: string; html_url?: string };
    const latest = release.tag_name ?? '';
    if (!latest || !isNewer(latest, app.version)) {
      ElMessage.success(`当前已是最新版本：v${app.version}`);
      return;
    }
    await ElMessageBox.confirm(`发现新版本 ${latest}，是否打开发布页面？`, '发现新版本', {
      confirmButtonText: '打开发布页',
      cancelButtonText: '稍后',
    });
    await openExternal(release.html_url ?? `${GITHUB_URL}/releases`);
  } catch (error) {
    const message = String(error);
    if (message === 'cancel' || message === 'close') return;
    ElMessage.error(`检查更新失败：${message}`);
  }
};
</script>
<style scoped lang="scss">
.shell {
  height: 100vh;
}
.sidebar {
  background: #172033;
  color: #d9e1ee;
  display: flex;
  flex-direction: column;
}
.brand {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 22px;
  font-size: 20px;
  font-weight: 700;
}
.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  display: grid;
  place-items: center;
}
.nav {
  border: 0;
  background: transparent;
  flex: 1;
}
.nav :deep(.el-menu-item) {
  color: #c2cada;
  height: 46px;
}
.nav :deep(.el-menu-item.is-active) {
  color: #fff;
  background: #263655;
}
.nav :deep(.el-menu-item:hover) {
  background: #202e49;
}
.sidebar-foot {
  padding: 18px 22px;
  color: #aab7cb;
  font-size: 13px;
  line-height: 1.9;
}
.sidebar-actions {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  margin: 8px -10px 4px;
}
.sidebar-action {
  justify-content: flex-start;
  color: #aab7cb;
  min-height: 30px;
}
.sidebar-action:hover {
  color: #fff;
  background: #202e49;
}
.version {
  color: #72809a;
}
.main {
  padding: 0;
  background: #f5f7fa;
  overflow: auto;
}
</style>
