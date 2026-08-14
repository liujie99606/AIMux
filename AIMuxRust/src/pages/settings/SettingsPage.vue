<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">设置</h2>
      <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
    </div>
    <el-card
      ><el-form :model="form" label-width="160px" style="max-width: 680px"
        ><el-form-item label="监听地址"><el-input v-model="form.host" /></el-form-item
        ><el-form-item label="端口"
          ><el-input-number v-model="form.port" :min="1" :max="65535" /></el-form-item
        ><el-form-item label="数据库路径"
          ><el-input v-model="form.db_path" placeholder="留空使用系统数据目录" /></el-form-item
        ><el-form-item label="上游超时（秒）"
          ><el-input-number v-model="form.upstream_timeout_seconds" :min="1" /></el-form-item
        ><el-form-item label="首字超时（秒）"
          ><el-input-number v-model="form.first_token_timeout_seconds" :min="1" /></el-form-item
        ><el-form-item label="重试次数"
          ><el-input-number
            v-model="form.request_retry_attempts"
            :min="1"
            :max="20" /></el-form-item
        ><el-form-item label="账号监控"
          ><el-switch v-model="form.monitoring_enabled" /></el-form-item
        ><el-form-item label="启用上游代理"
          ><el-switch v-model="form.upstream_proxy_enabled" /></el-form-item
        ><el-form-item label="上游代理地址"
          ><el-input v-model="form.upstream_proxy_url" /></el-form-item
        ><el-form-item label="本地令牌"
          ><el-input v-model="form.local_token" show-password /></el-form-item
        ><el-form-item label="数据目录"
          ><el-button @click="openDataDirectory">打开数据目录</el-button></el-form-item
        ></el-form
      ></el-card
    >
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { settingsApi, type Settings } from '../../api/settings';
import { invoke } from '@tauri-apps/api/core';
const form = reactive<Settings>({
  host: '127.0.0.1',
  port: 7789,
  db_path: '',
  upstream_timeout_seconds: 300,
  first_token_timeout_seconds: 60,
  request_retry_attempts: 10,
  upstream_proxy_enabled: false,
  upstream_proxy_url: 'http://127.0.0.1:7890',
  monitoring_enabled: true,
  local_token: '',
  launch_at_login: false,
});
const saving = ref(false);
onMounted(async () => Object.assign(form, await settingsApi.get()));
const save = async () => {
  saving.value = true;
  try {
    await settingsApi.update(form);
    ElMessage.success('设置已保存');
  } finally {
    saving.value = false;
  }
};
const openDataDirectory = () =>
  invoke('open_data_directory').catch((e) => ElMessage.error(String(e)));
</script>
