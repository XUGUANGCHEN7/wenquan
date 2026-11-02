const test = require("node:test")
const assert = require("node:assert/strict")
const { parseRoomCode } = require("../utils/room-code")

test("parses independent room QR parameters without granting identity", () => {
  assert.equal(parseRoomCode({ scene: "ROOM-05" }), "ROOM-05")
  assert.equal(parseRoomCode({ scene: "room-06" }), "ROOM-06")
  assert.equal(parseRoomCode({ q: "https://example.test/entry?scene=ROOM-07" }), "ROOM-07")
  assert.equal(parseRoomCode({}), "ROOM-01")
})
