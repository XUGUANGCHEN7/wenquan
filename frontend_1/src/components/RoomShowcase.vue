<script setup>
defineProps({
  image: { type: String, required: true },
  badge: { type: String, default: "" },
  title: { type: String, required: true },
  description: { type: String, default: "" },
  price: { type: String, required: true },
  unit: { type: String, default: "" },
  tags: { type: Array, default: () => [] },
  note: { type: String, default: "" },
})

const emit = defineEmits(["select"])
</script>

<template>
  <view class="room-showcase" @tap="emit('select')">
    <view class="room-media">
      <image class="room-image" mode="aspectFill" :src="image" lazy-load />
      <view class="room-media-shade" />
      <view v-if="badge" class="room-badge">
        <wd-tag type="warning" variant="light" size="small" round>{{ badge }}</wd-tag>
      </view>
      <view class="room-media-note">
        <text class="media-note-mark sn-serif">汤</text>
        <text>私汤 · 独立空间</text>
      </view>
    </view>

    <view class="room-body">
      <view class="room-heading">
        <text class="room-title sn-serif">{{ title }}</text>
        <view class="room-price">
          <text class="price-symbol">¥</text>
          <text class="price-value">{{ price }}</text>
          <text v-if="unit" class="price-unit">{{ unit }}</text>
        </view>
      </view>

      <text v-if="description" class="room-desc">{{ description }}</text>

      <view v-if="tags.length" class="room-tags">
        <wd-tag
          v-for="tag in tags"
          :key="tag"
          type="primary"
          variant="light"
          size="small"
          round
          custom-class="room-tag"
        >
          {{ tag }}
        </wd-tag>
      </view>

      <view class="room-footer">
        <text v-if="note" class="room-note">{{ note }}</text>
        <wd-button
          size="small"
          round
          variant="soft"
          custom-class="room-action"
          @click.stop="emit('select')"
        >
          查看房型
        </wd-button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.room-showcase {
  overflow: hidden;
  border: 1rpx solid var(--sn-line);
  border-radius: 32rpx;
  background: var(--sn-card);
  box-shadow: var(--sn-shadow-card);
}

.room-media {
  position: relative;
  height: 366rpx;
  overflow: hidden;
  background: #dce9e2;
}

.room-image {
  width: 100%;
  height: 100%;
}

.room-media-shade {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: linear-gradient(180deg, rgba(17, 45, 37, 0.02) 30%, rgba(17, 45, 37, 0.58) 100%);
}

.room-badge {
  position: absolute;
  top: 22rpx;
  left: 22rpx;
}

.room-media-note {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 22rpx;
  display: flex;
  align-items: center;
  gap: 10rpx;
  color: rgba(255, 255, 255, 0.86);
  font-size: 19rpx;
  letter-spacing: 1rpx;
}

.media-note-mark {
  width: 38rpx;
  height: 38rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1rpx solid rgba(255, 255, 255, 0.58);
  border-radius: 50%;
  font-size: 20rpx;
}

.room-body {
  padding: 28rpx 26rpx 24rpx;
}

.room-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}

.room-title {
  padding-top: 4rpx;
  color: var(--sn-ink);
  font-size: 36rpx;
  font-weight: 600;
  line-height: 1.35;
}

.room-price {
  flex: none;
  display: flex;
  align-items: baseline;
  color: #966d35;
}

.price-symbol {
  margin-right: 2rpx;
  font-size: 20rpx;
  font-weight: 600;
}

.price-value {
  font-size: 38rpx;
  font-weight: 700;
  letter-spacing: -1rpx;
}

.price-unit {
  margin-left: 4rpx;
  color: var(--sn-muted);
  font-size: 18rpx;
}

.room-desc {
  display: block;
  margin-top: 12rpx;
  color: var(--sn-muted);
  font-size: 22rpx;
  line-height: 1.7;
}

.room-tags {
  margin-top: 20rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.room-footer {
  margin-top: 24rpx;
  padding-top: 20rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  border-top: 1rpx solid #f0ebe1;
}

.room-note {
  color: var(--sn-muted);
  font-size: 18rpx;
  line-height: 1.5;
}

:deep(.room-tag) {
  padding: 4rpx 13rpx;
  font-size: 17rpx;
  line-height: 1.4;
}

:deep(.room-action) {
  min-width: 148rpx;
  min-height: 58rpx;
  padding: 0 22rpx;
  font-size: 21rpx;
  font-weight: 600;
}
</style>
