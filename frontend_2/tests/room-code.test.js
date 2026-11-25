import test from "node:test"
import assert from "node:assert/strict"
import { parseRoomCode } from "../src/utils/room-code.js"

test("parses independent room QR parameters without granting identity", () => {
  assert.equal(parseRoomCode({ scene: "ROOM-05" }), "ROOM-05")
  assert.equal(parseRoomCode({ scene: "room-06" }), "ROOM-06")
  assert.equal(parseRoomCode({ q: "https://example.test/entry?scene=ROOM-07" }), "ROOM-07")
  assert.equal(parseRoomCode({}), "ROOM-01")
})
