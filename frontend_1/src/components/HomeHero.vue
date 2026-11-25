<script setup>
import { ref } from "vue"

const props = defineProps({
  slides: { type: Array, default: () => [] },
})

const current = ref(0)

function onChange(event) {
  current.value = event.detail.current
}
</script>

<template>
  <view class="home-hero">
    <swiper
      class="hero-swiper"
      :circular="true"
      :autoplay="true"
      :interval="5600"
      :duration="650"
      @change="onChange"
    >
      <swiper-item v-for="slide in props.slides" :key="slide.image">
        <image class="hero-image" mode="aspectFill" :src="slide.image" />
        <view class="hero-shade" />
        <view
          v-if="slide.eyebrow || slide.title || slide.description"
          class="hero-copy"
        >
          <text class="hero-eyebrow">{{ slide.eyebrow }}</text>
          <text class="hero-title sn-serif">{{ slide.title }}</text>
          <text class="hero-desc">{{ slide.description }}</text>
        </view>
      </swiper-item>
    </swiper>

    <view class="hero-fade" />

    <view class="hero-nav">
      <view class="brand-lockup">
        <view class="brand-seal sn-serif">蜀</view>
        <view class="brand-copy">
          <text class="brand-cn sn-serif">蜀南温泉</text>
        </view>
      </view>
    </view>

    <view class="hero-bottom">
      <view class="hero-dots">
        <view
          v-for="(slide, index) in props.slides"
          :key="slide.image"
          class="hero-dot"
          :class="{ active: current === index }"
        />
      </view>
    </view>
  </view>
</template>

<style scoped>
.home-hero {
  position: relative;
  height: 664rpx;
  overflow: hidden;
  color: #fff;
  background: #173f39;
}

.hero-swiper,
.hero-image {
  width: 100%;
  height: 100%;
}

.hero-shade {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background:
    linear-gradient(180deg, rgba(11, 35, 30, 0.54) 0%, rgba(11, 35, 30, 0.02) 38%),
    linear-gradient(0deg, rgba(11, 35, 30, 0.82) 0%, rgba(11, 35, 30, 0.08) 66%);
}

.hero-fade {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 120rpx;
  z-index: 2;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(248, 246, 241, 0) 0%,
    rgba(248, 246, 241, 0.45) 38%,
    rgba(248, 246, 241, 0.92) 68%,
    #f8f6f1 100%
  );
}

.hero-nav {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 3;
  padding: calc(var(--status-bar-height, 44rpx) + 24rpx) 34rpx 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.brand-seal {
  width: 66rpx;
  height: 66rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  color: #f0d9b5;
  background: rgba(255, 255, 255, 0.09);
  font-size: 32rpx;
  line-height: 1;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 3rpx;
}

.brand-cn {
  font-size: 28rpx;
  font-weight: 600;
  letter-spacing: 3rpx;
}

.hero-copy {
  position: absolute;
  left: 38rpx;
  right: 38rpx;
  bottom: 128rpx;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-eyebrow {
  color: rgba(255, 255, 255, 0.72);
  font-size: 17rpx;
  letter-spacing: 5rpx;
}

.hero-title {
  max-width: 590rpx;
  margin: 18rpx 0 14rpx;
  white-space: pre-line;
  font-size: 60rpx;
  font-weight: 500;
  line-height: 1.32;
  letter-spacing: 4rpx;
  text-shadow: 0 4rpx 22rpx rgba(0, 0, 0, 0.2);
}

.hero-desc {
  color: rgba(255, 255, 255, 0.78);
  font-size: 23rpx;
  letter-spacing: 1rpx;
  line-height: 1.6;
}

.hero-bottom {
  position: absolute;
  left: 38rpx;
  right: 38rpx;
  bottom: 96rpx;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.hero-dots {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.hero-dot {
  width: 12rpx;
  height: 6rpx;
  border-radius: 6rpx;
  background: rgba(255, 255, 255, 0.42);
  transition: width 0.25s ease, background 0.25s ease;
}

.hero-dot.active {
  width: 34rpx;
  background: #f2dfbd;
}
</style>
