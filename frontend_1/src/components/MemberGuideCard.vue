<script setup>
defineProps({
  profile: { type: Object, default: null },
})

const emit = defineEmits(["action"])
</script>

<template>
  <view class="member-guide">
    <view class="guide-copy">
      <text class="guide-title sn-serif">注册享丰富会员权益</text>
      <text class="guide-subtitle">立即加入，享受专属温泉礼遇</text>
    </view>

    <view class="guide-action">
      <template v-if="profile">
        <wd-button size="small" round variant="soft" custom-class="guide-button" @click="emit('action')">
          会员中心
        </wd-button>
      </template>
      <template v-else>
        <wd-button size="small" round variant="soft" custom-class="guide-button" @click="emit('action')">
          成为会员
        </wd-button>
      </template>
    </view>
  </view>
</template>

<style scoped>
.member-guide {
  margin-bottom: 24rpx;
  padding: 26rpx 26rpx 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  overflow: hidden;
  border: 1rpx solid #eadfcd;
  border-radius: 28rpx;
  background: linear-gradient(120deg, #fffdf8 0%, #f5ecd9 100%);
  box-shadow: var(--sn-shadow-soft);
}

.guide-copy {
  min-width: 0;
}

.guide-title,
.guide-subtitle {
  display: block;
}

.guide-title {
  color: var(--sn-ink);
  font-size: 30rpx;
  font-weight: 600;
  line-height: 1.35;
}

.guide-subtitle {
  margin-top: 7rpx;
  color: var(--sn-muted);
  font-size: 20rpx;
  line-height: 1.5;
}

.guide-action {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5rpx;
  max-width: 230rpx;
}

:deep(.guide-button.wd-button) {
  margin-top: 5rpx;
  min-height: 56rpx;
  padding: 0 18rpx;
  color: #ffffff !important;
  background: #0f8a63 !important;
  font-size: 21rpx;
  font-weight: 700 !important;
  white-space: nowrap;
}

:deep(.guide-button.wd-button.wd-button--active) {
  background: #0b6f50 !important;
}

:deep(.guide-button .wd-button__text) {
  color: #ffffff !important;
  font-weight: 700 !important;
}
</style>
