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
        ><el-divider content-position="left">API 请求地址</el-divider
        ><el-form-item label="OpenAI 请求地址"
          ><div class="address-field">
            <el-input :model-value="openaiAddress" readonly
              ><template #append
                ><el-button
                  title="复制 OpenAI 请求地址"
                  @click="copyAddress('OpenAI', openaiAddress)"
                  ><el-icon><CopyDocument /></el-icon>复制</el-button
                ></template
              ></el-input
            >
          </div></el-form-item
        ><el-form-item label="Anthropic 请求地址"
          ><div class="address-field">
            <el-input :model-value="anthropicAddress" readonly
              ><template #append
                ><el-button
                  title="复制 Anthropic 请求地址"
                  @click="copyAddress('Anthropic', anthropicAddress)"
                  ><el-icon><CopyDocument /></el-icon>复制</el-button
                ></template
              ></el-input
            >
          </div></el-form-item
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
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { CopyDocument } from '@element-plus/icons-vue';
import { settingsApi, type Settings } from '../../api/settings';
import { invoke } from '@tauri-apps/api/core';
const form = reactive<Settings>({
  host: '127.0.0.1',
  port: 7789,
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
const gatewayHost = computed(() => {
  const host = form.host.trim();
  return !host || host === '0.0.0.0' ? '127.0.0.1' : host;
});
const gatewayOrigin = computed(() => `http://${gatewayHost.value}:${form.port}`);
const openaiAddress = computed(() => `${gatewayOrigin.value}/v1`);
const anthropicAddress = computed(() => gatewayOrigin.value);

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

const copyAddress = async (name: string, address: string) => {
  try {
    await navigator.clipboard.writeText(address);
    ElMessage.success(`${name} 请求地址已复制`);
  } catch (error) {
    ElMessage.error(`复制失败：${String(error)}`);
  }
};
</script>

<style scoped lang="scss">
.address-field {
  display: flex;
  width: 100%;
}

.address-field :deep(.el-input) {
  flex: 1;
}
</style>
