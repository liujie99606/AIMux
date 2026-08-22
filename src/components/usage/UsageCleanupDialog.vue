<template>
  <el-dialog v-model="visible" title="清除历史记录" width="420px">
    <el-form label-width="120px">
      <el-form-item label="清理范围">
        <el-radio-group v-model="days">
          <el-radio :value="7">清除 7 天前数据</el-radio>
          <el-radio :value="30">清除 30 天前数据</el-radio>
          <el-radio :value="90">清除 90 天前数据</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="loading" @click="visible = false">取消</el-button>
      <el-button type="danger" :loading="loading" @click="$emit('confirm', days)">
        确认清除
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const visible = defineModel<boolean>({ required: true });
withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  { loading: false },
);
defineEmits<{
  confirm: [days: number];
}>();

const days = ref(7);
watch(visible, (isVisible) => {
  if (isVisible) days.value = 7;
});
</script>
