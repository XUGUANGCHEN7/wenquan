<script setup lang="ts">
defineProps<{ loading: boolean; error: string; empty: boolean; emptyText?: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="loading" class="data-state"><span class="spinner" />正在读取服务端数据…</div>
  <div v-else-if="error" class="data-state error"><strong>操作未完成</strong><p>{{ error }}</p><button class="button secondary" @click="$emit('retry')">重新加载</button></div>
  <div v-else-if="empty" class="data-state">{{ emptyText ?? "当前没有记录" }}</div>
  <slot v-else />
</template>
