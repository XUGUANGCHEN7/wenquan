<script setup>
defineProps({
  image: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: "" },
})

const emit = defineEmits(["select"])
</script>

<template>
  <view class="journey-card" hover-class="journey-card-pressed" @tap="emit('select')">
    <image class="journey-image" :src="image" mode="aspectFit" />
    <text class="journey-title sn-serif">{{ title }}</text>
    <text v-if="description" class="journey-desc">{{ description }}</text>
  </view>
</template>

<style scoped>
.journey-card {
  min-width: 0;
  padding: 8rpx 12rpx 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.journey-card-pressed {
  opacity: 0.7;
}

.journey-image {
  display: block;
  width: 220rpx;
  max-width: 100%;
  height: 220rpx;
}

.journey-title {
  margin-top: 8rpx;
  color: var(--sn-ink);
  font-size: 34rpx;
  font-weight: 600;
  line-height: 1.4;
}

.journey-desc {
  margin-top: 10rpx;
  color: var(--sn-muted);
  font-size: 21rpx;
  line-height: 1.6;
}
</style>
