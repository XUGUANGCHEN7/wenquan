// 内置二维码渲染库（无 npm 依赖）
// 支持：byte 模式 / 纠错级 M / 自动版本 1-6（载荷 ≤ 100 个 ASCII 字符）
// 用法：qrcode.draw(canvasNode, text, cssSize)，canvasNode 为 type="2d" 的 canvas 节点

// ---------- GF(256) 伽罗瓦域 ----------
const EXP = new Array(256)
const LOG = new Array(256)
;(function initMath() {
  let x = 1
  for (let i = 0; i < 255; i++) {
    EXP[i] = x
    LOG[x] = i
    x <<= 1
    if (x & 0x100) x ^= 0x11d
  }
  EXP[255] = EXP[0]
})()

function glog(n) {
  if (n < 1) throw new Error("glog(" + n + ")")
  return LOG[n]
}

function gexp(n) {
  while (n < 0) n += 255
  while (n >= 256) n -= 255
  return EXP[n]
}

// ---------- 多项式（RS 纠错用） ----------
function QRPolynomial(num, shift) {
  let offset = 0
  while (offset < num.length && num[offset] === 0) offset++
  this.num = new Array(num.length - offset + shift)
  for (let i = 0; i < num.length - offset; i++) this.num[i] = num[i + offset]
}

QRPolynomial.prototype = {
  getLength() {
    return this.num.length
  },
  multiply(e) {
    const num = new Array(this.getLength() + e.getLength() - 1)
    for (let i = 0; i < num.length; i++) num[i] = 0
    for (let i = 0; i < this.getLength(); i++) {
      for (let j = 0; j < e.getLength(); j++) {
        num[i + j] ^= gexp(glog(this.num[i]) + glog(e.num[j]))
      }
    }
    return new QRPolynomial(num, 0)
  },
  mod(e) {
    if (this.getLength() - e.getLength() < 0) return this
    const ratio = glog(this.num[0]) - glog(e.num[0])
    const num = this.num.slice()
    for (let i = 0; i < e.getLength(); i++) {
      num[i] ^= gexp(glog(e.num[i]) + ratio)
    }
    return new QRPolynomial(num, 0).mod(e)
  }
}

// ---------- RS 分块表（纠错级 M，版本 1-6）[块数, 每块总码字, 每块数据码字] ----------
const RS_BLOCKS_M = [
  [[1, 26, 16]],
  [[1, 44, 28]],
  [[1, 70, 44]],
  [[2, 50, 32]],
  [[2, 67, 43]],
  [[4, 43, 27]]
]

// 各版本对齐图案中心坐标
const PATTERN_POSITIONS = [[], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34]]

// 纠错级 M + 掩码 0 经过 BCH 与固定掩码异或后的格式信息（常量）
const FORMAT_INFO_M0 = 0x5412

function createDataCodewords(text) {
  const bytes = []
  for (let i = 0; i < text.length; i++) bytes.push(text.charCodeAt(i) & 0xff)

  // 选版本：数据位 = 4(模式) + 8(字符数) + 8*n，需留 ≥4 位终止符
  let typeNumber = 0
  for (let v = 1; v <= 6; v++) {
    const capacityBits = RS_BLOCKS_M[v - 1].reduce((s, b) => s + b[2], 0) * 8
    if (4 + 8 + bytes.length * 8 + 4 <= capacityBits) {
      typeNumber = v
      break
    }
  }
  if (!typeNumber) throw new Error("payload too long for QR v1-6 (M)")

  const buffer = { buffer: [], length: 0 }
  function putBit(bit) {
    const bufIndex = Math.floor(buffer.length / 8)
    if (buffer.buffer.length <= bufIndex) buffer.buffer.push(0)
    if (bit) buffer.buffer[bufIndex] |= 0x80 >>> (buffer.length % 8)
    buffer.length++
  }
  function put(num, length) {
    for (let i = 0; i < length; i++) putBit((num >>> (length - i - 1)) & 1)
  }

  put(0b0100, 4) // byte 模式
  put(text.length, 8) // 版本 1-9 字符数为 8 位
  bytes.forEach((b) => put(b, 8))

  const blocks = RS_BLOCKS_M[typeNumber - 1]
  const totalData = blocks.reduce((s, b) => s + b[2], 0)
  const totalCodewords = blocks.reduce((s, b) => s + b[1], 0)

  // 终止符（最多 4 位 0）
  put(0, Math.min(4, totalData * 8 - buffer.length))
  // 对齐到字节
  if (buffer.length % 8 !== 0) put(0, 8 - (buffer.length % 8))
  // 交替填充 0xEC / 0x11
  const padBytes = []
  while (padBytes.length + buffer.buffer.length < totalData) padBytes.push(0xec, 0x11)
  padBytes.slice(0, totalData - buffer.buffer.length).forEach((b) => buffer.buffer.push(b))
  while (buffer.buffer.length > totalData) buffer.buffer.pop()

  // 分块计算 RS 纠错码并交织
  let offset = 0
  let maxDc = 0
  let maxEc = 0
  const dcdata = []
  const ecdata = []
  blocks.forEach((block) => {
    const dcCount = block[2]
    const ecCount = block[1] - dcCount
    maxDc = Math.max(maxDc, dcCount)
    maxEc = Math.max(maxEc, ecCount)

    const dc = new Array(dcCount)
    for (let i = 0; i < dcCount; i++) dc[i] = buffer.buffer[i + offset]
    offset += dcCount
    dcdata.push(dc)

    let rsPoly = new QRPolynomial([1], 0)
    for (let i = 0; i < ecCount; i++) {
      rsPoly = rsPoly.multiply(new QRPolynomial([1, gexp(i)], 0))
    }
    const rawPoly = new QRPolynomial(dc, rsPoly.getLength() - 1)
    const modPoly = rawPoly.mod(rsPoly)
    const ec = new Array(rsPoly.getLength() - 1)
    for (let i = 0; i < ec.length; i++) {
      const modIndex = i + modPoly.getLength() - ec.length
      ec[i] = modIndex >= 0 ? modPoly.num[modIndex] : 0
    }
    ecdata.push(ec)
  })

  const result = new Array(totalCodewords)
  let index = 0
  for (let i = 0; i < maxDc; i++) {
    for (let j = 0; j < dcdata.length; j++) {
      if (i < dcdata[j].length) result[index++] = dcdata[j][i]
    }
  }
  for (let i = 0; i < maxEc; i++) {
    for (let j = 0; j < ecdata.length; j++) {
      if (i < ecdata[j].length) result[index++] = ecdata[j][i]
    }
  }
  return { codewords: result, typeNumber }
}

// ---------- 矩阵构建 ----------
function makeMatrix(text) {
  const { codewords, typeNumber } = createDataCodewords(text)
  const moduleCount = 17 + 4 * typeNumber
  const modules = []
  for (let r = 0; r < moduleCount; r++) {
    modules.push(new Array(moduleCount).fill(null))
  }

  function setupPositionProbePattern(row, col) {
    for (let r = -1; r <= 7; r++) {
      if (row + r <= -1 || moduleCount <= row + r) continue
      for (let c = -1; c <= 7; c++) {
        if (col + c <= -1 || moduleCount <= col + c) continue
        modules[row + r][col + c] =
          (0 <= r && r <= 6 && (c === 0 || c === 6)) ||
          (0 <= c && c <= 6 && (r === 0 || r === 6)) ||
          (2 <= r && r <= 4 && 2 <= c && c <= 4)
      }
    }
  }

  function setupPositionAdjustPattern() {
    const pos = PATTERN_POSITIONS[typeNumber - 1]
    for (let i = 0; i < pos.length; i++) {
      for (let j = 0; j < pos.length; j++) {
        const row = pos[i]
        const col = pos[j]
        if (modules[row][col] !== null) continue
        for (let r = -2; r <= 2; r++) {
          for (let c = -2; c <= 2; c++) {
            modules[row + r][col + c] = Math.max(Math.abs(r), Math.abs(c)) !== 1
          }
        }
      }
    }
  }

  function setupTimingPattern() {
    for (let r = 8; r < moduleCount - 8; r++) {
      if (modules[r][6] === null) modules[r][6] = r % 2 === 0
    }
    for (let c = 8; c < moduleCount - 8; c++) {
      if (modules[6][c] === null) modules[6][c] = c % 2 === 0
    }
  }

  function setupTypeInfo() {
    // 纠错级 M(00) + 掩码 0(000) → 格式信息为常量 0x5412
    for (let i = 0; i < 15; i++) {
      const mod = ((FORMAT_INFO_M0 >> i) & 1) === 1
      if (i < 6) modules[i][8] = mod
      else if (i < 8) modules[i + 1][8] = mod
      else modules[moduleCount - 15 + i][8] = mod
    }
    for (let i = 0; i < 15; i++) {
      const mod = ((FORMAT_INFO_M0 >> i) & 1) === 1
      if (i < 8) modules[8][moduleCount - i - 1] = mod
      else if (i < 9) modules[8][15 - i - 1 + 1] = mod
      else modules[8][15 - i - 1] = mod
    }
    modules[moduleCount - 8][8] = true // 固定暗模块
  }

  function mapData() {
    // 掩码 0：(row + col) % 2 === 0 时取反
    let row = moduleCount - 1
    let inc = -1
    let bitIndex = 7
    let byteIndex = 0
    for (let col = moduleCount - 1; col > 0; col -= 2) {
      if (col === 6) col--
      for (;;) {
        for (let c = 0; c < 2; c++) {
          if (modules[row][col - c] === null) {
            let dark = false
            if (byteIndex < codewords.length) {
              dark = ((codewords[byteIndex] >>> bitIndex) & 1) === 1
            }
            if ((row + (col - c)) % 2 === 0) dark = !dark
            modules[row][col - c] = dark
            bitIndex--
            if (bitIndex === -1) {
              byteIndex++
              bitIndex = 7
            }
          }
        }
        row += inc
        if (row < 0 || row >= moduleCount) {
          row -= inc
          inc = -inc
          break
        }
      }
    }
  }

  setupPositionProbePattern(0, 0)
  setupPositionProbePattern(moduleCount - 7, 0)
  setupPositionProbePattern(0, moduleCount - 7)
  setupPositionAdjustPattern()
  setupTimingPattern()
  setupTypeInfo()
  mapData()

  return { modules, moduleCount }
}

// ---------- 绘制到 canvas 2d ----------
function draw(canvasNode, text, cssSize) {
  const { modules, moduleCount } = makeMatrix(text)
  const quiet = 2
  const total = moduleCount + quiet * 2
  let dpr = 2
  try {
    dpr = wx.getSystemInfoSync().pixelRatio || 2
  } catch (e) {
    dpr = 2
  }
  const px = Math.max(1, Math.floor(cssSize * dpr))
  canvasNode.width = px
  canvasNode.height = px
  const ctx = canvasNode.getContext("2d")
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.fillStyle = "#ffffff"
  ctx.fillRect(0, 0, px, px)
  const unit = px / total
  ctx.fillStyle = "#1a1a1a"
  for (let r = 0; r < moduleCount; r++) {
    for (let c = 0; c < moduleCount; c++) {
      if (modules[r][c]) {
        ctx.fillRect(Math.floor((c + quiet) * unit), Math.floor((r + quiet) * unit), Math.ceil(unit), Math.ceil(unit))
      }
    }
  }
}

module.exports = { draw, makeMatrix }
