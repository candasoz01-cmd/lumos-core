import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { runInNewContext } from "node:vm";

const source = await readFile(new URL("../ui/src/pages/canli-ses.astro", import.meta.url), "utf8");
const script = source.match(/<script is:inline>([\s\S]*?)<\/script>/)[1];

async function session() {
  const elements = new Map();
  const calls = { tracks: 0, peer: 0, channel: 0, pause: 0, native: 0 };
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      dataset: {}, listeners: {}, srcObject: {},
      setAttribute() {},
      pause() { calls.pause++; },
      addEventListener(name, listener) { this.listeners[name] = listener; },
    });
    return elements.get(id);
  };
  const track = { enabled: true, stop() { calls.tracks++; } };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  const listeners = [];
  const channel = {
    readyState: "open", send() {}, close() { calls.channel++; this.readyState = "closed"; },
    addEventListener(name, listener) {
      assert.equal(name, "message");
      listeners.push(listener);
    },
  };
  let peer;
  const connected = Promise.withResolvers();
  const context = {
    document: { getElementById: element },
    location: { hash: "#token=synthetic-test", pathname: "/canli-ses" },
    history: { replaceState() {} }, URLSearchParams,
    navigator: { mediaDevices: { getUserMedia: async () => stream } },
    fetch: async () => ({ ok: true, text: async () => "synthetic-answer" }),
    RTCPeerConnection: class {
      constructor() { peer = this; this.connectionState = "new"; }
      addTrack() {}
      createDataChannel() { return channel; }
      async createOffer() { return { sdp: "synthetic-offer" }; }
      async setLocalDescription() {}
      async setRemoteDescription() {
        this.connectionState = "connected";
        this.onconnectionstatechange();
        connected.resolve();
      }
      close() {
        calls.peer++;
        this.connectionState = "closed";
        this.onconnectionstatechange?.();
      }
    },
  };
  runInNewContext(script, context);
  // Match build 50: its document-end script wraps the page's channel factory.
  const original = context.RTCPeerConnection.prototype.createDataChannel;
  context.RTCPeerConnection.prototype.createDataChannel = function (...args) {
    const result = original.apply(this, args);
    result.addEventListener("message", () => { calls.native++; });
    return result;
  };
  element("toggle").listeners.click();
  await connected.promise;
  const emit = (event) => {
    let stopped = false;
    const message = {
      data: typeof event === "string" ? event : JSON.stringify(event),
      stopImmediatePropagation() { stopped = true; },
    };
    for (const listener of listeners) {
      listener(message);
      if (stopped) break;
    }
    return stopped;
  };
  return { calls, element, emit, peer, channel };
}

const userTranscript = (text) => ({
  type: "conversation.item.input_audio_transcription.completed",
  item_id: "synthetic-user-turn", transcript: text,
});

for (const command of [
  "Kendini kapat", "Lumos, kendini kapat.", "Lütfen görüşmeyi bitir!",
  "Canlı görüşmeyi kapat", "Konuşmayı bitir", "Canlı sesi kapat",
  "Hoşça kal", "Hoşçakal, görüşürüz.", "Tamam, görüşürüz",
  "Lumos lütfen kendini kapat", "KENDİNİ KAPAT", "  görüşürüz!  ",
]) {
  test(`spoken end releases microphone and closes the session: ${command}`, async () => {
    const s = await session();
    assert.equal(s.emit(userTranscript(command)), true);
    assert.deepEqual(s.calls, { tracks: 1, peer: 1, channel: 1, pause: 1, native: 0 });
    assert.equal(s.peer.connectionState, "closed");
    assert.equal(s.channel.readyState, "closed");
    assert.equal(s.element("remote-audio").srcObject, null);
    assert.equal(s.element("orb").dataset.live, "false");
    assert.equal(s.element("toggle").dataset.stop, "false");
    assert.equal(s.element("toggle").disabled, true);
    // This existing label/disabled combination drives the iOS onEnded bridge.
    assert.equal(s.element("toggle").textContent, "Görüşme sona erdi");
    s.emit(userTranscript(command));
    assert.equal(s.calls.tracks, 1, "late duplicate must not repeat teardown");
    assert.equal(s.calls.peer, 1);
  });
}

for (const text of [
  "kendini kapat özelliğin var mı", "kendini kapat?", "görüşmeyi kapatma",
  "kendini kapatma", "görüşmeyi bitirme", "görüşmeyi bitir demedim",
  '"kendini kapat"', "“görüşürüz”", "‘hoşça kal’", "Kendini kapat cümlesini söyle",
  "Ben hoşça kal dersem ne olur", "Eğer tamam dersem kendini kapat",
  "keşke kendini kapat", "sonra görüşürüz derim", "görüşürüz mü dedin",
  "arkadaşım hoşça kal dedi", "kendini kapat ama şimdi değil",
  "dur", "sus", "yeter", "tamam yeter", "sesi kapat", "oturumu kapat",
]) {
  test(`non-command remains with the existing iOS handler: ${text}`, async () => {
    const s = await session();
    assert.equal(s.emit(userTranscript(text)), false);
    assert.deepEqual(s.calls, { tracks: 0, peer: 0, channel: 0, pause: 0, native: 1 });
    assert.equal(s.peer.connectionState, "connected");
  });
}

test("only completed user transcripts can end a connected session", async () => {
  const s = await session();
  for (const event of [
    "not json", null, {},
    { type: "response.output_audio_transcript.done", transcript: "kendini kapat" },
    { type: "conversation.item.input_audio_transcription.delta", delta: "kendini kapat" },
    { ...userTranscript("kendini kapat"), item_id: "" },
    userTranscript(null), userTranscript({ text: "kendini kapat" }),
  ]) assert.equal(s.emit(event), false);
  s.peer.connectionState = "connecting";
  assert.equal(s.emit(userTranscript("kendini kapat")), false);
  assert.equal(s.calls.tracks, 0);
});

test("manual end still uses the same resource cleanup", async () => {
  const s = await session();
  s.element("toggle").listeners.click();
  assert.deepEqual(s.calls, { tracks: 1, peer: 1, channel: 1, pause: 1, native: 0 });
});
