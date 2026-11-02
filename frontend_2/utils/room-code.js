const config = require("../config")

function valid(value) {
  return value && /^[A-Za-z0-9_-]{2,80}$/.test(value) ? value.toUpperCase() : null
}

function parseRoomCode(options = {}) {
  const scene = valid(options.scene ? decodeURIComponent(options.scene) : null)
  if (scene) return scene
  if (options.q) {
    const url = decodeURIComponent(options.q)
    const match = url.match(/[?&](?:scene|room)=([^&]+)/)
    const fromUrl = valid(match && match[1])
    if (fromUrl) return fromUrl
  }
  return config.devRoomCode
}
module.exports = { parseRoomCode }
