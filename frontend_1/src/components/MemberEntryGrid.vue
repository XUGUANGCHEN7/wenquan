<script setup>
defineProps({ items: { type: Array, default: () => [] }, columns: { type: Number, default: 4 } })
const emit = defineEmits(['select'])
</script>
<template>
  <view class="member-entry-grid" :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }">
    <button v-for="item in items" :key="item.key" class="member-entry" hover-class="member-entry-pressed" @tap="emit('select', item.key)">
      <view class="member-entry-icon"><wd-icon :name="item.icon" size="42rpx" /></view>
      <text>{{ item.label }}</text>
    </button>
  </view>
</template>
<style scoped>
.member-entry-grid { display: grid; gap: 8rpx; margin-top: 26rpx; }
.member-entry { min-width: 0; margin: 0; padding: 8rpx 0; display: flex; flex-direction: column; align-items: center; gap: 14rpx; border-radius: 16rpx; background: transparent; color: #263f38; font-size: 21rpx; line-height: 1.5; }
.member-entry::after { border: 0; }
.member-entry-icon { display: flex; justify-content: center; align-items: center; width: 70rpx; height: 70rpx; border-radius: 22rpx; color: #246b61; background: #f0f3eb; }
.member-entry-pressed { background: #f4f6ee; }
</style>
