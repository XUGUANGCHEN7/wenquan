<script setup lang="ts">
import { statusText } from "../utils/format"
defineProps<{ status: string }>()
</script>

<template><span class="status-badge" :data-status="status">{{ statusText(status) }}</span></template>
