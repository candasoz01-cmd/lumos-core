// Live voice: transient disconnect recovery, timeouts, permission denial and
// a real microphone mute. Everything runs against synthetic WebRTC fakes;
// no network, no OpenAI session and no real microphone are used.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { runInNewContext } from "node:vm";

const source = await readFile(new URL("../ui/src/pages/canli-ses.astro", import.meta.url), "utf8");
const script = source.match(/<script is:inline>([\s\S]*?)<\/script>/)[1];

function fakeTimers() {
  let now = 0;
  let nextId = 1;
  const pending = new Map();
  return {
    setTimeout(fn, ms) {
      const id = nextId++;
      pending.set(id, { fn, at: now + ms, ms });
      return id;
    },
    clearTimeout(id) { pending.delete(id); },
    delays() { return [...pending.values()].map((t) => t.ms); },
    size() { return pending.size; },
    // Advance virtual time, firing due timers in order.
    advance(ms) {
      const target = now + ms;
      for (;;) {
        const due = [...pending.entries()]
          .filter(([, t]) => t.at <= target)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        pending.delete(due[0]);
        now = due[1].at;
        due[1].fn();
      }
      now = target;
    },
  };
}

async function session(options = {}) {
  const elements = new Map();
  const calls = { tracks: 0, peer: 0, channel: 0, pause: 0, fetch: 0, replace: [] };
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      dataset: {}, listeners: {}, srcObject: {}, muted: false, attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; },
      pause() { calls.pause++; },
      addEventListener(name, listener) { this.listeners[name] = listener; },
    });
    return elements.get(id);
  };
  const track = { kind: "audio", enabled: true, stop() { calls.tracks++; this.readyState = "ended"; } };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  // The sender models what actually leaves the device: an audio frame is
  // transmitted only while a live, enabled track is attached.
  const sender = {
    track: null,
    framesSent: 0,
    replaceTrack(next) {
      calls.replace.push(next === null ? null : "track");
      if (options.replaceFails) return Promise.reject(new Error("synthetic"));
      this.track = next;
      return Promise.resolve();
    },
    pump(frames = 1) {
      for (let i = 0; i < frames; i++) {
        if (this.track && this.track.enabled && this.track.readyState !== "ended") this.framesSent++;
      }
    },
  };
  const channel = {
    readyState: "open", sent: [],
    send(message) { this.sent.push(JSON.parse(message)); },
    close() { calls.channel++; this.readyState = "closed"; },
    addEventListener() {},
  };
  const timers = fakeTimers();
  let peer;
  const connected = Promise.withResolvers();
  const context = {
    document: { getElementById: element },
    location: { hash: options.noToken ? "" : "#token=synthetic-test", pathname: "/canli-ses" },
    history: { replaceState() {} }, URLSearchParams,
    navigator: {
      mediaDevices: {
        getUserMedia: async () => {
          if (options.denyMicrophone) {
            const error = new Error("denied");
            error.name = options.denyMicrophone;
            throw error;
          }
          return stream;
        },
      },
    },
    fetch: async (_url, init) => {
      calls.fetch++;
      if (options.hangFetch) {
        return new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => {
            const error = new Error("aborted");
            error.name = "AbortError";
            reject(error);
          });
        });
      }
      return { ok: !options.sessionRejected, text: async () => "synthetic-answer" };
    },
    setTimeout: timers.setTimeout,
    clearTimeout: timers.clearTimeout,
    AbortController,
    RTCPeerConnection: class {
      constructor() { peer = this; this.connectionState = "new"; }
      addTrack(addedTrack) {
        sender.track = addedTrack;
        return sender;
      }
      createDataChannel() { return channel; }
      async createOffer() { return { sdp: "synthetic-offer" }; }
      async setLocalDescription() {}
      async setRemoteDescription() {
        if (options.neverConnects) {
          this.connectionState = "connecting";
          this.onconnectionstatechange?.();
        } else {
          this.connectionState = "connected";
          this.onconnectionstatechange?.();
        }
        connected.resolve();
      }
      close() {
        calls.peer++;
        this.connectionState = "closed";
        // Real browsers do not fire connectionstatechange on close(); the
        // page must not depend on it, but must also survive it.
        this.onconnectionstatechange?.();
      }
    },
  };
  runInNewContext(script, context);
  element("toggle").listeners.click();
  const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
  if (options.denyMicrophone || options.sessionRejected || options.hangFetch || options.noToken) {
    await settle();
  } else {
    await connected.promise;
  }
  await settle();
  const setState = (state) => {
    peer.connectionState = state;
    peer.onconnectionstatechange?.();
  };
  return { calls, element, peer: () => peer, track, sender, channel, timers, setState, settle };
}

const ended = (s) => {
  assert.equal(s.element("toggle").textContent, "Görüşme sona erdi", "iOS onEnded bridge label");
  assert.equal(s.element("toggle").disabled, true);
  assert.equal(s.element("remote-audio").srcObject, null);
  assert.equal(s.element("orb").dataset.live, "false");
  assert.equal(s.element("mute").hidden, true);
};

// --- Transient disconnect recovery ------------------------------------------

test("a transient disconnect does not end the call and recovers on the same peer", async () => {
  const s = await session();
  const peerBefore = s.peer();
  s.setState("disconnected");
  assert.equal(s.calls.peer, 0, "peer must not be closed on disconnected");
  assert.equal(s.calls.tracks, 0, "microphone must not be released on disconnected");
  assert.match(s.element("status").textContent, /yeniden bağlanılıyor/);
  assert.equal(s.element("orb").dataset.live, "false");
  s.timers.advance(1500);
  s.setState("connected");
  assert.equal(s.peer(), peerBefore, "no new peer or session is created");
  assert.equal(s.calls.fetch, 1, "no second session request");
  assert.equal(s.timers.size(), 0, "recovery checks are cancelled once connected");
  assert.equal(s.element("orb").dataset.live, "true");
  assert.equal(s.element("toggle").textContent, "Görüşmeyi bitir");
  assert.equal(s.element("status").textContent, "Canlı — konuşabilirsin");
});

test("recovery checks back off 1 s, 2 s, 4 s, 8 s and end the call after 15 s", async () => {
  const s = await session();
  s.setState("disconnected");
  const seen = [];
  for (const step of [1000, 2000, 4000, 8000]) {
    seen.push(...s.timers.delays());
    s.timers.advance(step);
  }
  assert.deepEqual(seen, [1000, 2000, 4000, 8000]);
  assert.equal(s.calls.peer, 1);
  assert.equal(s.calls.tracks, 1);
  assert.equal(s.calls.channel, 1);
  assert.match(s.element("status").textContent, /Bağlantı geri gelmedi/);
  ended(s);
  assert.equal(s.timers.size(), 0, "no stray timers after teardown");
});

test("still disconnected just before the deadline keeps the call", async () => {
  const s = await session();
  s.setState("disconnected");
  s.timers.advance(14999);
  assert.equal(s.calls.peer, 0);
  s.timers.advance(1);
  assert.equal(s.calls.peer, 1);
});

test("failed during recovery ends the call once with full cleanup", async () => {
  const s = await session();
  s.setState("disconnected");
  s.setState("failed");
  assert.deepEqual(
    { tracks: s.calls.tracks, peer: s.calls.peer, channel: s.calls.channel, pause: s.calls.pause },
    { tracks: 1, peer: 1, channel: 1, pause: 1 },
  );
  ended(s);
  s.timers.advance(20000);
  assert.equal(s.calls.peer, 1, "teardown is not repeated by a late recovery check");
});

test("a second disconnected while recovering does not restart the backoff", async () => {
  const s = await session();
  s.setState("disconnected");
  s.timers.advance(3000);
  s.setState("disconnected");
  s.timers.advance(12000);
  assert.equal(s.calls.peer, 1, "deadline still 15 s after the first disconnect");
});

test("push-to-talk microphone closes while the link is down", async () => {
  const s = await session();
  s.element("mode-push").listeners.click();
  s.element("push-to-talk").listeners.pointerdown({ preventDefault() {}, pointerId: 1 });
  assert.equal(s.track.enabled, true);
  s.setState("disconnected");
  assert.equal(s.track.enabled, false);
  assert.equal(s.element("push-to-talk").hidden, true);
  assert.equal(s.element("remote-audio").muted, false);
});

// --- Microphone mute ---------------------------------------------------------

test("mute detaches the microphone from the sender: no audio frames leave", async () => {
  const s = await session();
  assert.equal(s.element("mute").hidden, false);
  s.sender.pump(5);
  assert.equal(s.sender.framesSent, 5, "baseline: audio flows while unmuted");
  s.element("mute").listeners.click();
  await s.settle();
  assert.equal(s.sender.track, null, "sender carries no track while muted");
  assert.equal(s.track.enabled, false, "track is disabled as a second barrier");
  s.sender.pump(50);
  assert.equal(s.sender.framesSent, 5, "zero frames sent during mute");
  assert.equal(s.element("mute").attributes["aria-pressed"], "true");
  assert.equal(s.element("mute").textContent, "Mikrofonu aç");
  assert.match(s.element("status").textContent, /Mikrofon kapalı/);
  assert.equal(s.calls.tracks, 0, "mute is not teardown: permission stays granted");
});

test("unmute reattaches the same track and audio flows again", async () => {
  const s = await session();
  s.element("mute").listeners.click();
  await s.settle();
  s.element("mute").listeners.click();
  await s.settle();
  assert.equal(s.sender.track, s.track);
  assert.equal(s.track.enabled, true);
  s.sender.pump(3);
  assert.equal(s.sender.framesSent, 3);
  assert.deepEqual(s.calls.replace, [null, "track"]);
  assert.equal(s.element("mute").attributes["aria-pressed"], "false");
  assert.equal(s.element("status").textContent, "Canlı — konuşabilirsin");
});

test("mute persists across mode switches, push-to-talk and recovery", async () => {
  const s = await session();
  s.element("mute").listeners.click();
  await s.settle();
  s.element("mode-push").listeners.click();
  s.element("push-to-talk").listeners.pointerdown({ preventDefault() {}, pointerId: 1 });
  assert.equal(s.track.enabled, false, "holding push-to-talk cannot reopen a muted mic");
  assert.match(s.element("status").textContent, /önce mikrofonu aç/);
  assert.equal(s.channel.sent.length, 0, "muted press does not interrupt the model");
  s.element("mode-auto").listeners.click();
  assert.equal(s.track.enabled, false, "switching to free talk cannot unmute");
  s.setState("disconnected");
  s.timers.advance(2000);
  s.setState("connected");
  await s.settle();
  assert.equal(s.track.enabled, false, "recovery cannot unmute");
  assert.equal(s.sender.track, null);
  s.sender.pump(10);
  assert.equal(s.sender.framesSent, 0);
  assert.equal(s.element("mute").attributes["aria-pressed"], "true");
});

test("unmute in push-to-talk keeps the mic closed until the button is held", async () => {
  const s = await session();
  s.element("mode-push").listeners.click();
  s.element("mute").listeners.click();
  await s.settle();
  s.element("mute").listeners.click();
  await s.settle();
  assert.equal(s.track.enabled, false);
  s.element("push-to-talk").listeners.pointerdown({ preventDefault() {}, pointerId: 1 });
  assert.equal(s.track.enabled, true);
});

test("if detaching fails the track stays disabled (fail closed)", async () => {
  const s = await session({ replaceFails: true });
  s.element("mute").listeners.click();
  await s.settle();
  assert.equal(s.track.enabled, false);
  s.sender.pump(10);
  assert.equal(s.sender.framesSent, 0);
});

test("ending a muted call still releases the microphone", async () => {
  const s = await session();
  s.element("mute").listeners.click();
  await s.settle();
  s.element("toggle").listeners.click();
  assert.equal(s.calls.tracks, 1);
  assert.equal(s.calls.peer, 1);
  ended(s);
});

// --- Start-up failures -------------------------------------------------------

for (const [name, pattern] of [
  ["NotAllowedError", /Mikrofon izni verilmedi/],
  ["SecurityError", /Mikrofon izni verilmedi/],
  ["NotFoundError", /mikrofon bulunamadı/],
  ["NotReadableError", /başka bir uygulama/],
  ["AbortError", /başka bir uygulama/],
]) {
  test(`microphone ${name} shows a clear message and leaves nothing open`, async () => {
    const s = await session({ denyMicrophone: name });
    assert.match(s.element("status").textContent, pattern);
    assert.equal(s.calls.fetch, 0, "no session request without a microphone");
    assert.equal(s.calls.peer, 1, "the prepared peer is closed");
    assert.equal(s.element("mute").hidden, true);
    assert.equal(s.timers.size(), 0, "connect timer cleared");
    assert.notEqual(s.element("toggle").textContent, "Görüşme sona erdi",
      "a start failure must not fire the iOS ended bridge");
  });
}

test("a rejected session releases the microphone and peer", async () => {
  const s = await session({ sessionRejected: true });
  assert.equal(s.calls.tracks, 1);
  assert.equal(s.calls.peer, 1);
  assert.equal(s.calls.channel, 1);
  assert.match(s.element("status").textContent, /başlatılamadı/);
  assert.equal(s.timers.size(), 0);
});

test("a hanging session request is aborted after 15 s", async () => {
  const s = await session({ hangFetch: true });
  assert.equal(s.calls.tracks, 0);
  s.timers.advance(15000);
  await s.settle();
  assert.match(s.element("status").textContent, /zamanında yanıt vermedi/);
  assert.equal(s.calls.tracks, 1);
  assert.equal(s.calls.peer, 1);
  assert.equal(s.timers.size(), 0);
});

test("a peer that never connects is torn down after 20 s", async () => {
  const s = await session({ neverConnects: true });
  s.timers.advance(19999);
  assert.equal(s.calls.peer, 0);
  s.timers.advance(1);
  assert.match(s.element("status").textContent, /zaman aşımına uğradı/);
  assert.equal(s.calls.tracks, 1);
  assert.equal(s.calls.peer, 1);
});

test("the connect timer is cleared once connected", async () => {
  const s = await session();
  assert.equal(s.timers.size(), 0);
  s.timers.advance(60000);
  assert.equal(s.calls.peer, 0);
});

test("mute is not offered before the call connects or without a token", async () => {
  const s = await session({ noToken: true });
  assert.notEqual(s.element("mute").hidden, false);
  assert.equal(s.calls.fetch, 0);
});
