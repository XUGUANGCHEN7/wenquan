<script setup>
import { copyOrderCode } from "../pages/orders/detail-state.js"
defineProps({ label: { type: String, required: true }, code: { type: String, required: true } })
</script>

<template>
  <view class="order-code-row">
    <view class="order-code-copy">
      <text class="order-code-label">{{ label }}</text>
      <text class="order-code-value" selectable>{{ code }}</text>
    </view>
    <button class="order-copy-button" :aria-label="'复制' + label" hover-class="order-copy-pressed" @tap="copyOrderCode(code)">
      <view class="order-copy-glyph" />
    </button>
  </view>
</template>

<style scoped>
.order-code-row { display: flex; align-items: center; gap: 18rpx; }
.order-code-copy { flex: 1; min-width: 0; }
.order-code-label { display: block; color: var(--sn-muted); font-size: 23rpx; line-height: 1.5; }
.order-code-value { display: block; margin-top: 9rpx; color: var(--sn-ink); font-size: 25rpx; line-height: 1.65; word-break: break-all; font-variant-numeric: tabular-nums; }
.order-copy-button { flex: none; display: flex; align-items: center; justify-content: center; width: 60rpx; height: 60rpx; margin: 0; padding: 0; color: var(--sn-green); background: transparent; border-radius: 14rpx; }
.order-copy-glyph { position: relative; width: 22rpx; height: 27rpx; border: 2rpx solid currentColor; border-radius: 4rpx; }
.order-copy-glyph::before { content: ""; position: absolute; top: -8rpx; left: -8rpx; width: 18rpx; height: 22rpx; border-top: 2rpx solid currentColor; border-left: 2rpx solid currentColor; border-radius: 4rpx 0 0 0; }
.order-copy-pressed { background: var(--sn-green-soft); }
</style>
