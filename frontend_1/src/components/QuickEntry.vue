<script setup>
defineProps({
  mark: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: "" },
  tone: { type: String, default: "green" },
})

const emit = defineEmits(["select"])
</script>

<template>
  <view class="quick-entry" @tap="emit('select')">
    <view class="quick-mark" :class="`is-${tone}`">{{ mark }}</view>
    <text class="quick-title">{{ title }}</text>
    <text v-if="description" class="quick-desc">{{ description }}</text>
  </view>
</template>

<style scoped>
.quick-entry {
  min-width: 0;
  min-height: 176rpx;
  padding: 22rpx 12rpx 18rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  border: 1rpx solid var(--sn-line);
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.82);
}

.quick-mark {
  width: 58rpx;
  height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18rpx;
  font-family: "STSong", "Songti SC", serif;
  font-size: 26rpx;
  font-weight: 600;
}

.quick-mark.is-green {
  color: var(--sn-green);
  background: var(--sn-green-soft);
}

.quick-mark.is-gold {
  color: #976f34;
  background: var(--sn-gold-soft);
}

.quick-mark.is-clay {
  color: #a25f3e;
  background: #f7e8dc;
}

.quick-title {
  margin-top: 12rpx;
  color: var(--sn-ink);
  font-size: 23rpx;
  font-weight: 600;
  line-height: 1.4;
  text-align: center;
}

.quick-desc {
  margin-top: 4rpx;
  color: var(--sn-muted);
  font-size: 17rpx;
  line-height: 1.4;
  text-align: center;
}
</style>
