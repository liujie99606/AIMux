<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">监控管理</h2>
      <div>
        <el-tag :type="enabled ? 'success' : 'info'">
          {{ enabled ? '监控已开启' : '监控已关闭' }}
        </el-tag>
        <el-button style="margin-left: 12px" :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border class="compact-table">
      <el-table-column prop="account_name" label="账号" min-width="140" />
      <el-table-column prop="account_type" label="类型" width="90" />
      <el-table-column prop="multiplier" label="倍率" width="80">
        <template #default="{ row }">{{ Number(row.multiplier).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="测试模型" min-width="140">
        <template #default="{ row }">
          {{ row.model || latest(row.records)?.model || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="最近检查" width="170">
        <template #default="{ row }">{{ formatTime(latest(row.records)?.checked_at) }}</template>
      </el-table-column>
      <el-table-column label="平均耗时" width="105">
        <template #default="{ row }">
          <span :class="avg(row.records) > SLOW_THRESHOLD ? 'warning-text' : ''">
            {{ avgText(row.records) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="结果" width="75">
        <template #default="{ row }">
          <span
            v-if="latest(row.records)"
            :class="latest(row.records)?.success ? 'success-text' : 'failure-text'"
          >
            {{ latest(row.records)?.success ? '成功' : '失败' }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="最近30次检测记录" min-width="620">
        <template #default="{ row }">
          <div class="checks">
            <span
              v-for="(record, index) in normalized(row.records)"
              :key="index"
              class="check"
              :class="cellClass(record)"
              :title="cellTitle(record)"
            />
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { monitorApi, type MonitorItem, type MonitorRecord } from '../../api/monitor';

const STATUS_COUNT = 30;
const SLOW_THRESHOLD = 20_000;
const items = ref<MonitorItem[]>([]);
const loading = ref(false);
const enabled = ref(false);
let timer: number | undefined;

const load = async () => {
  if (loading.value) return;
  loading.value = true;
  try {
    const result = await monitorApi.list();
    items.value = result.items;
    enabled.value = result.monitoring_enabled;
  } finally {
    loading.value = false;
  }
};

const latest = (records: MonitorRecord[]) => records.at(-1);

const normalized = (records: MonitorRecord[]) => {
  const recent = records.slice(-STATUS_COUNT);
  const emptyCount = STATUS_COUNT - recent.length;
  return Array.from({ length: STATUS_COUNT }, (_, index) => recent[index - emptyCount] ?? null);
};

const avg = (records: MonitorRecord[]) => {
  const durations = records
    .map((record) => record.duration_ms)
    .filter((duration): duration is number => duration != null);
  return durations.length
    ? durations.reduce((sum, duration) => sum + duration, 0) / durations.length
    : 0;
};

const avgText = (records: MonitorRecord[]) =>
  avg(records) ? `${(avg(records) / 1000).toFixed(2)} 秒` : '-';

const formatTime = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
};

const cellClass = (record: MonitorRecord | null) => {
  if (!record) return 'empty';
  if (!record.success) return 'fail';
  return (record.duration_ms ?? 0) > SLOW_THRESHOLD ? 'slow' : 'ok';
};

const cellTitle = (record: MonitorRecord | null) => {
  if (!record) return '暂无监控记录';
  const result = record.success ? '成功' : '失败';
  const duration =
    record.duration_ms == null ? '-' : `${(record.duration_ms / 1000).toFixed(2)} 秒`;
  const error = record.success ? '' : `，错误：${record.error_message || record.error_code || '-'}`;
  return `${formatTime(record.checked_at)}，${result}，耗时：${duration}，状态码：${record.status_code ?? '-'}${error}`;
};

onMounted(() => {
  load();
  timer = window.setInterval(load, 30_000);
});
onUnmounted(() => {
  if (timer !== undefined) window.clearInterval(timer);
});
</script>

<style scoped>
.checks {
  display: flex;
  gap: 0;
  height: 26px;
  align-items: center;
}

.check {
  display: block;
  width: 20px;
  height: 20px;
  border-right: 1px solid white;
}

.empty {
  background: #9ca3af;
}

.ok {
  background: #2e9f63;
}

.fail {
  background: #c43d4b;
}

.slow {
  background: #e0a800;
}

.check:first-child {
  border-radius: 3px 0 0 3px;
}

.check:last-child {
  border-radius: 0 3px 3px 0;
}

.success-text {
  color: #2e9f63;
}

.failure-text {
  color: #c43d4b;
  font-weight: 600;
}
</style>
