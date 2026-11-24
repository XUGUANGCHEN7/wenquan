<script>
import { generateQRCode } from "../utils/order-qr-encoder.js"

export default {
  name: "OrderQrImage",
  props: { text: { type: String, required: true } },
  emits: ["error"],
  data() {
    return { canvasId: `order-qr-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      imagePath: "", failed: false, canvasSize: uni.upx2px(320), generation: 0 }
  },
  mounted() { this.renderCode() },
  beforeUnmount() { this.generation++ },
  watch: { text() { this.renderCode() } },
  methods: {
    async renderCode() {
      const current = ++this.generation
      this.imagePath = ""; this.failed = false
      if (!this.text) return
      await this.$nextTick()
      if (current !== this.generation) return
      uni.createSelectorQuery().in(this).select(`#${this.canvasId}`).node(result => {
        if (current !== this.generation) return
        try {
          if (!result?.node) throw new Error("二维码画布未就绪")
          const canvas = result.node
          const ratio = (uni.getWindowInfo ? uni.getWindowInfo() : uni.getSystemInfoSync()).pixelRatio || 1
          const size = Math.max(320, Math.round(this.canvasSize * ratio))
          canvas.width = size; canvas.height = size
          const ctx = canvas.getContext("2d")
          const { modules, moduleCount } = generateQRCode(this.text)
          const count = moduleCount + 8
          ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, size, size)
          ctx.fillStyle = "#153e37"
          modules.forEach((row, y) => row.forEach((dark, x) => {
            if (!dark) return
            const left = Math.round((x + 4) * size / count), top = Math.round((y + 4) * size / count)
            ctx.fillRect(left, top, Math.round((x + 5) * size / count) - left, Math.round((y + 5) * size / count) - top)
          }))
          uni.canvasToTempFilePath({ canvas, width: size, height: size, destWidth: size, destHeight: size,
            success: response => { if (current === this.generation) this.imagePath = response.tempFilePath },
            fail: error => this.fail(error, current),
          })
        } catch (error) { this.fail(error, current) }
      }).exec()
    },
    fail(error, current) {
      if (current !== this.generation) return
      this.failed = true; this.$emit("error", error)
    },
  },
}
</script>

<template>
  <view class="order-qr-frame">
    <image v-if="imagePath" class="order-qr-image" :src="imagePath" mode="aspectFit" aria-label="订单核验二维码" />
    <text v-else class="order-qr-placeholder">{{ failed ? '请使用订单编号查询' : '二维码生成中…' }}</text>
    <view class="order-qr-render-stage" aria-hidden="true" :style="{ width: canvasSize + 'px', height: canvasSize + 'px' }">
      <canvas :id="canvasId" type="2d" :style="{ width: canvasSize + 'px', height: canvasSize + 'px' }" />
    </view>
  </view>
</template>

<style scoped>
.order-qr-frame { position: relative; display: flex; align-items: center; justify-content: center; width: 320rpx; height: 320rpx; margin: 0 auto; background: #fff; }
.order-qr-image { display: block; width: 320rpx; height: 320rpx; }
.order-qr-placeholder { color: var(--sn-muted); font-size: 23rpx; }
.order-qr-render-stage { position: fixed; left: -10000rpx; top: 0; overflow: hidden; opacity: 0; pointer-events: none; }
.order-qr-render-stage canvas { position: absolute; left: 0; top: 0; display: block; }
</style>
