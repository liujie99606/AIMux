<template>
  <div class="page">
    <div class="page-toolbar">
      <h2 class="page-title">账号管理</h2>
      <div>
        <el-button :loading="store.loading" @click="load">刷新</el-button>
        <el-button type="primary" @click="open()">新增账号</el-button>
      </div>
    </div>

    <el-table :data="store.items" v-loading="store.loading" class="compact-table" border stripe>
      <el-table-column prop="name" label="名称" min-width="170" />
      <el-table-column prop="multiplier" label="倍率" width="90">
        <template #default="{ row }">
          <span>{{ Number(row.multiplier).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-button link :type="row.status === 'active' ? 'success' : 'info'" @click="toggle(row)">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="130">
        <template #default="{ row }">
          <el-input-number
            v-model="row.priority"
            :min="0"
            :max="9"
            size="small"
            @change="priority(row)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="test_default_model" label="测试默认模型" min-width="150" />
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="open(row)">编辑</el-button>
          <el-button link type="warning" @click="test(row)">测试</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialog"
      :title="editing ? '编辑账号' : '新增账号'"
      width="920px"
      top="4vh"
      destroy-on-close
      class="account-dialog"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="110px"
        label-position="right"
        class="account-form"
      >
        <el-form-item label="名称" prop="name" required>
          <el-input v-model="form.name" autofocus />
        </el-form-item>
        <el-form-item label="类型" prop="type" required>
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
          </el-select>
        </el-form-item>
        <el-form-item label="上游地址" prop="base_url" required>
          <el-input v-model="form.base_url" />
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key" required>
          <el-input v-model="form.api_key" show-password placeholder="必填" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority" required>
          <el-input-number v-model="form.priority" :min="0" :max="9" />
        </el-form-item>
        <el-form-item label="倍率" prop="multiplier" required>
          <el-input-number
            v-model="form.multiplier"
            :min="0.01"
            :max="0.3"
            :step="0.01"
            :precision="2"
          />
        </el-form-item>
        <el-form-item label="支持模型" prop="supported_models" required>
          <div class="model-picker">
            <el-checkbox-group v-model="form.supported_models">
              <el-checkbox v-for="model in modelOptions" :key="model.id" :label="model.name">
                {{ model.name }}
              </el-checkbox>
            </el-checkbox-group>
            <span v-if="!modelOptions.length" class="muted">该协议暂无模型目录</span>
          </div>
        </el-form-item>
        <el-form-item label="测试默认模型" prop="test_default_model" required>
          <el-select
            v-model="form.test_default_model"
            clearable
            style="width: 100%"
            :disabled="!form.supported_models.length"
            placeholder="使用模型维护默认值"
          >
            <el-option
              v-for="name in selectedModelOptions"
              :key="name"
              :label="name"
              :value="name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型映射">
          <div class="mapping-section">
            <el-table
              :data="mappingRows"
              border
              height="180"
              class="mapping-table"
              empty-text="暂无模型映射"
            >
              <el-table-column label="客户端模型" min-width="280">
                <template #default="{ row }">
                  <el-select
                    v-model="row.client_model"
                    placeholder="选择客户端模型"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="name in form.supported_models"
                      :key="name"
                      :label="name"
                      :value="name"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="上游模型" min-width="280">
                <template #default="{ row }">
                  <el-select
                    v-model="row.upstream_model"
                    placeholder="选择上游模型"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="model in upstreamModelOptions"
                      :key="model"
                      :label="model"
                      :value="model"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ $index }">
                  <el-button link type="danger" @click="removeMapping($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button class="mapping-add" plain size="small" @click="addMapping">
              <el-icon><Plus /></el-icon>
              新增映射
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="tagsText" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
    <AccountTestDialog
      v-if="testAccount"
      v-model="testDialog"
      :account="testAccount"
      :models="testModels"
      @finished="load"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import { accountsApi, type Account } from '../../api/accounts';
import { useAccountsStore } from '../../stores/accounts';
import { useModelsStore } from '../../stores/models';
import AccountTestDialog from '../../components/accounts/AccountTestDialog.vue';

type AccountForm = {
  id?: string;
  name: string;
  type: Account['type'];
  base_url: string;
  api_key: string;
  priority: number;
  multiplier: number;
  supported_models: string[];
  test_default_model: string;
  tags: string[];
  notes: string;
};

type MappingRow = {
  client_model: string;
  upstream_model: string;
};

const store = useAccountsStore();
const models = useModelsStore();
const dialog = ref(false);
const editing = ref(false);
const formRef = ref<FormInstance>();
const tagsText = ref('');
const mappingRows = ref<MappingRow[]>([]);
const testDialog = ref(false);
const testAccount = ref<Account>();

const createForm = (): AccountForm => ({
  name: '',
  type: 'openai',
  base_url: '',
  api_key: '',
  priority: 5,
  multiplier: 0.1,
  supported_models: [],
  test_default_model: '',
  tags: [],
  notes: '',
});

const form = reactive<AccountForm>(createForm());

const modelOptions = computed(() => models.byType(form.type));
const testModels = computed(() => models.byType(testAccount.value?.type ?? 'openai'));
const selectedModelOptions = computed(() => form.supported_models);
const upstreamModelOptions = computed(() => {
  const names = modelOptions.value.map((model) => model.name);
  for (const row of mappingRows.value) {
    if (row.upstream_model && !names.includes(row.upstream_model)) names.push(row.upstream_model);
  }
  return names;
});

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  base_url: [{ required: true, message: '请输入上游地址', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API 密钥', trigger: 'blur' }],
  priority: [{ required: true, type: 'number', message: '请输入优先级', trigger: 'change' }],
  multiplier: [{ required: true, type: 'number', message: '请输入倍率', trigger: 'change' }],
  supported_models: [
    {
      validator: (_rule, value, callback) =>
        value?.length ? callback() : callback(new Error('请至少选择一个支持模型')),
      trigger: 'change',
    },
  ],
  test_default_model: [{ required: true, message: '请选择测试默认模型', trigger: 'change' }],
};

const load = async () => {
  await Promise.all([store.load(), models.load()]);
};

const open = async (row?: Account) => {
  if (!models.items.length) await models.load();
  editing.value = !!row;
  const supportedModels = [...(row?.supported_models ?? [])];
  if (row?.test_default_model && !supportedModels.includes(row.test_default_model)) {
    supportedModels.push(row.test_default_model);
  }
  Object.assign(
    form,
    row
      ? {
          ...row,
          supported_models: supportedModels,
          test_default_model: row.test_default_model ?? '',
          tags: row.tags ?? [],
          notes: row.notes ?? '',
        }
      : createForm(),
  );
  tagsText.value = row?.tags?.join(', ') ?? '';
  mappingRows.value = Object.entries(row?.model_mappings ?? {}).map(
    ([client_model, upstream_model]) => ({ client_model, upstream_model }),
  );
  dialog.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

const addMapping = () => {
  mappingRows.value.push({ client_model: '', upstream_model: '' });
};

const removeMapping = (index: number) => {
  mappingRows.value.splice(index, 1);
};

const serializeMappings = (): Record<string, string> | null => {
  const mappings: Record<string, string> = {};
  for (const [index, row] of mappingRows.value.entries()) {
    const client = row.client_model.trim();
    const upstream = row.upstream_model.trim();
    if (!client || !upstream) {
      throw new Error(`模型映射第 ${index + 1} 行不能为空`);
    }
    if (mappings[client]) {
      throw new Error(`模型映射中客户端模型重复：${client}`);
    }
    if (client === upstream) {
      throw new Error(`模型映射第 ${index + 1} 行的两个模型不能相同`);
    }
    mappings[client] = upstream;
  }
  return Object.keys(mappings).length ? mappings : null;
};

const save = async () => {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  try {
    const payload = {
      ...form,
      tags: tagsText.value
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      notes: form.notes.trim(),
      model_mappings: serializeMappings() ?? {},
    };
    if (editing.value && form.id) await accountsApi.update(form.id, payload);
    else await accountsApi.create(payload);
    dialog.value = false;
    await store.load();
    ElMessage.success('保存成功');
  } catch (error) {
    ElMessage.error(String(error));
  }
};

const toggle = async (row: Account) => {
  await accountsApi.toggle(row.id);
  await store.load();
};

const priority = async (row: Account) => {
  await accountsApi.priority(row.id, row.priority);
  await store.load();
};

const remove = async (row: Account) => {
  await ElMessageBox.confirm(`确认删除 ${row.name}？`, '提示');
  await accountsApi.remove(row.id);
  await store.load();
};

const test = async (row: Account) => {
  if (!models.items.length) await models.load();
  testAccount.value = row;
  testDialog.value = true;
};

watch(
  () => form.type,
  () => {
    const available = new Set(modelOptions.value.map((model) => model.name));
    form.supported_models = form.supported_models.filter((name) => available.has(name));
    if (!form.supported_models.includes(form.test_default_model)) form.test_default_model = '';
  },
);

watch(
  () => [...form.supported_models],
  (selected) => {
    if (!selected.includes(form.test_default_model)) form.test_default_model = '';
    for (const row of mappingRows.value) {
      if (row.client_model && !selected.includes(row.client_model)) row.client_model = '';
    }
  },
);

onMounted(load);
</script>

<style scoped lang="scss">
.account-dialog :deep(.el-dialog__body) {
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.account-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.model-picker {
  width: 100%;
  min-height: 78px;
  max-height: 120px;
  overflow-y: auto;
  padding: 8px 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.model-picker :deep(.el-checkbox) {
  margin-right: 18px;
  margin-bottom: 6px;
}

.mapping-section {
  width: 100%;
}

.mapping-table {
  width: 100%;
}

.mapping-add {
  margin-top: 8px;
}
</style>
