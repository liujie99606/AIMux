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
        <div class="version">v{{ app.version }}</div>
      </div>
    </el-aside>
    <el-main class="main"><router-view /></el-main>
  </el-container>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { DataAnalysis, Grid, Monitor, Setting, Tickets, User } from '@element-plus/icons-vue';
import { useAppStore } from '../stores/app';
const route = useRoute();
const app = useAppStore();
onMounted(() => app.startClock());
const clock = computed(() => app.now.toLocaleTimeString('zh-CN', { hour12: false }));
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
.version {
  color: #72809a;
}
.main {
  padding: 0;
  background: #f5f7fa;
  overflow: auto;
}
</style>
