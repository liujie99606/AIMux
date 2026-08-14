<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">使用记录</h2>
      <div>
        <el-button @click="reset">重置</el-button>
        <el-button @click="cleanup">清除3天前数据</el-button>
      </div>
    </div>

    <el-form inline class="usage-filter" @submit.prevent="queryFromFirstPage">
      <el-form-item label="筛选">
        <el-input v-model="filters.account_id" placeholder="账号 ID" clearable />
      </el-form-item>
      <el-form-item>
        <el-input v-model="filters.model" placeholder="模型" clearable />
      </el-form-item>
      <el-form-item>
        <el-select v-model="filters.kind" placeholder="全部类型" clearable>
          <el-option label="OpenAI" value="openai" />
          <el-option label="Anthropic" value="anthropic" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-select v-model="filters.success" placeholder="全部结果" clearable>
          <el-option label="成功" :value="true" />
          <el-option label="失败" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-input v-model="filters.started_after" placeholder="开始时间 ISO" clearable />
      </el-form-item>
      <el-form-item>
        <el-input v-model="filters.started_before" placeholder="结束时间 ISO" clearable />
      </el-form-item>
      <el-button type="primary" native-type="submit">查询</el-button>
    </el-form>

    <div class="summary-grid">
      <div class="metric">
        <div class="metric-label">请求数</div>
        <div class="metric-value">{{ summary.request_count }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">成功率</div>
        <div class="metric-value">{{ (summary.success_rate * 100).toFixed(2) }}%</div>
      </div>
      <div class="metric">
        <div class="metric-label">平均耗时</div>
        <div class="metric-value">{{ formatMs(summary.average_duration_ms) }}</div>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" border stripe class="compact-table">
      <el-table-column label="时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column prop="account_name" label="账号" min-width="140" />
      <el-table-column prop="account_type" label="类型" width="90" />
      <el-table-column prop="model" label="模型" min-width="150" />
      <el-table-column prop="reasoning_effort" label="推理强度" width="100" />
      <el-table-column prop="endpoint" label="接口" min-width="180" />
      <el-table-column label="结果" width="80">
        <template #default="{ row }">
          <span :class="row.success ? 'success-text' : 'failure-text'">
            {{ row.success ? '成功' : '失败' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="首Token" width="100">
        <template #default="{ row }">
          <span :class="(row.first_token_ms ?? 0) > 10_000 ? 'warning-text' : ''">
            {{ formatMs(row.first_token_ms) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="耗时" width="100">
        <template #default="{ row }">
          <span :class="(row.duration_ms ?? 0) > 20_000 ? 'warning-text' : ''">
            {{ formatMs(row.duration_ms) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="attempts" label="重试次数" width="90" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="showDetail(row.id)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="PAGE_SIZE"
      :total="total"
      layout="total, prev, pager, next"
      class="pagination"
      @current-change="load"
    />

    <el-dialog v-model="detailVisible" title="使用记录详情" width="920px" top="5vh">
      <template v-if="selected">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="记录 ID">{{ text(selected.id) }}</el-descriptions-item>
          <el-descriptions-item label="Trace ID">{{
            text(selected.trace_id)
          }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{
            formatTime(selected.started_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{
            formatTime(selected.ended_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="总耗时">{{
            formatMsRaw(selected.duration_ms)
          }}</el-descriptions-item>
          <el-descriptions-item label="首 Token 用时">{{
            formatMsRaw(selected.first_token_ms)
          }}</el-descriptions-item>
          <el-descriptions-item label="尝试次数">{{
            text(selected.attempts)
          }}</el-descriptions-item>
          <el-descriptions-item label="账号名称">{{
            text(selected.account_name)
          }}</el-descriptions-item>
          <el-descriptions-item label="账号 ID">{{
            text(selected.account_id)
          }}</el-descriptions-item>
          <el-descriptions-item label="账号类型">{{
            text(selected.account_type)
          }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ text(selected.model) }}</el-descriptions-item>
          <el-descriptions-item label="推理强度">{{
            text(selected.reasoning_effort)
          }}</el-descriptions-item>
          <el-descriptions-item label="接口">{{ text(selected.endpoint) }}</el-descriptions-item>
          <el-descriptions-item label="流式">{{
            selected.stream ? '是' : '否'
          }}</el-descriptions-item>
          <el-descriptions-item label="客户端 IP">{{
            text(selected.client_ip)
          }}</el-descriptions-item>
          <el-descriptions-item label="结果">{{
            selected.success ? '成功' : '失败'
          }}</el-descriptions-item>
          <el-descriptions-item label="状态码">{{
            text(selected.status_code)
          }}</el-descriptions-item>
          <el-descriptions-item label="错误码">{{
            text(selected.error_code)
          }}</el-descriptions-item>
        </el-descriptions>
        <div class="token-line">
          Token 用量：输入 {{ text(selected.input_tokens) }} / 输出
          {{ text(selected.output_tokens) }} / 缓存 {{ text(selected.cached_tokens) }} / 合计
          {{ text(selected.total_tokens) }}
        </div>
        <div class="error-title">错误信息：</div>
        <el-input
          :model-value="text(selected.error_message)"
          type="textarea"
          readonly
          :rows="5"
          class="error-view"
        />
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { usageApi, type UsageRecord } from '../../api/usage';

const PAGE_SIZE = 20;
const items = ref<UsageRecord[]>([]);
const total = ref(0);
const page = ref(1);
const loading = ref(false);
const filters = reactive({
  account_id: '',
  model: '',
  kind: '',
  success: undefined as boolean | undefined,
  started_after: '',
  started_before: '',
});
const summary = reactive({
  request_count: 0,
  success_rate: 0,
  average_duration_ms: 0,
  total_tokens: 0,
});
const detailVisible = ref(false);
const selected = ref<UsageRecord>();

const query = () => {
  const params = new URLSearchParams({
    offset: String((page.value - 1) * PAGE_SIZE),
    limit: String(PAGE_SIZE),
  });
  if (filters.account_id.trim()) params.set('account_id', filters.account_id.trim());
  if (filters.model.trim()) params.set('model', filters.model.trim());
  if (filters.kind) params.set('type', filters.kind);
  if (filters.success !== undefined) params.set('success', String(filters.success));
  if (filters.started_after.trim()) params.set('started_after', filters.started_after.trim());
  if (filters.started_before.trim()) params.set('started_before', filters.started_before.trim());
  return `?${params.toString()}`;
};

const load = async () => {
  loading.value = true;
  try {
    const result = await usageApi.list(query());
    items.value = result.items;
    total.value = result.total;
    Object.assign(summary, result.summary);
  } finally {
    loading.value = false;
  }
};

const queryFromFirstPage = () => {
  page.value = 1;
  load();
};

const reset = () => {
  filters.account_id = '';
  filters.model = '';
  filters.kind = '';
  filters.success = undefined;
  filters.started_after = '';
  filters.started_before = '';
  queryFromFirstPage();
};

const showDetail = async (id: string) => {
  selected.value = await usageApi.detail(id);
  detailVisible.value = true;
};

const cleanup = async () => {
  await ElMessageBox.confirm('清除三天以前的使用记录？', '确认');
  const result = await usageApi.cleanup();
  ElMessage.success(`已清除 ${result.deleted} 条`);
  queryFromFirstPage();
};

const formatTime = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
};

const formatMs = (value?: number) => (value == null ? '-' : `${(value / 1000).toFixed(2)} 秒`);
const formatMsRaw = (value?: number) => (value == null ? '-' : `${value} ms`);
const text = (value: unknown) => (value == null || value === '' ? '-' : String(value));

onMounted(load);
</script>

<style scoped>
.usage-filter {
  margin-bottom: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.pagination {
  justify-content: flex-end;
  margin-top: 14px;
}

.success-text {
  color: #2e9f63;
}

.failure-text {
  color: #c43d4b;
  font-weight: 600;
}

.token-line {
  padding: 14px 0;
  color: #344054;
}

.error-title {
  margin-bottom: 6px;
}

.error-view :deep(textarea) {
  font-family: Consolas, monospace;
}
</style>
