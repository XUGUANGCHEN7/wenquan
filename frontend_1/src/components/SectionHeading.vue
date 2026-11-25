<script setup>
defineProps({
  eyebrow: { type: String, default: "" },
  title: { type: String, required: true },
  action: { type: String, default: "" },
})

const emit = defineEmits(["action"])
</script>

<template>
  <view class="section-heading">
    <view class="heading-copy">
      <text v-if="eyebrow" class="sn-eyebrow heading-eyebrow">{{ eyebrow }}</text>
      <text class="heading-title sn-serif">{{ title }}</text>
    </view>
    <view v-if="action" class="heading-action" @tap="emit('action')">
      <text>{{ action }}</text>
      <text class="heading-arrow">›</text>
    </view>
  </view>
</template>

<style scoped>
.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24rpx;
  margin: 50rpx 0 24rpx;
}

.heading-copy {
  min-width: 0;
}

.heading-eyebrow {
  margin-bottom: 8rpx;
}

.heading-title {
  display: block;
  color: var(--sn-ink);
  font-size: 40rpx;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 1rpx;
}

.heading-action {
  flex: none;
  min-height: 64rpx;
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 8rpx 0 4rpx 18rpx;
  color: var(--sn-muted);
  font-size: 22rpx;
}

.heading-arrow {
  color: var(--sn-green);
  font-size: 30rpx;
  line-height: 1;
}
</style>
