const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");

test("manifest contains standalone identity and real PNG icons", () => {
    const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.webmanifest"), "utf8"));
    assert.equal(manifest.name, "PWA Radar");
    assert.equal(manifest.display, "standalone");
    assert.equal(manifest.start_url, "./");
    assert.equal(manifest.scope, "./");
    assert.equal(manifest.id, "./");
    for (const icon of manifest.icons) {
        const png = fs.readFileSync(path.join(root, icon.src));
        assert.equal(png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
        assert.equal(`${png.readUInt32BE(16)}x${png.readUInt32BE(20)}`, icon.sizes);
    }
    assert.ok(manifest.icons.some((icon) => icon.purpose === "maskable"));
});

test("sitemap indexes only the canonical public homepage", () => {
    const sitemap = fs.readFileSync(path.join(root, "sitemap.xml"), "utf8");
    const page = fs.readFileSync(path.join(root, "index.html"), "utf8");
    const methodology = fs.readFileSync(path.join(root, "metodologia.html"), "utf8");
    const robots = fs.readFileSync(path.join(root, "robots.txt"), "utf8");
    assert.match(sitemap, /^<\?xml version="1\.0" encoding="UTF-8"\?>/);
    assert.deepEqual([...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1]), [
        "https://pwaradar.it/",
        "https://pwaradar.it/metodologia.html"
    ]);
    assert.match(page, /<link rel="canonical" href="https:\/\/pwaradar\.it\/">/);
    assert.match(page, /href="\.\/metodologia\.html"/);
    assert.match(methodology, /<link rel="canonical" href="https:\/\/pwaradar\.it\/metodologia\.html">/);
    assert.match(methodology, /Europol/);
    assert.match(methodology, /non esegue JavaScript/i);
    assert.match(methodology, /non prova che il Service Worker sia assente/i);
    assert.match(robots, /^Sitemap: https:\/\/pwaradar\.it\/sitemap\.xml$/m);
});

function worker() {
    const handlers = {};
    const entries = new Map();
    const deleted = [];
    const cache = {
        addAll: async (paths) => {
            for (const url of paths) assert.ok(fs.existsSync(path.join(root, url)));
        },
        match: async (request) => entries.get(request.url),
        put: async (request, response) => entries.set(request.url, response)
    };
    const context = {
        URL, Set,
        self: {
            registration: { scope: "https://pwaradar.it/" },
            clients: { claim: async () => {} },
            addEventListener: (name, handler) => { handlers[name] = handler; }
        },
        caches: {
            open: async () => cache,
            keys: async () => ["pwa-radar-shell-v0", "pwa-radar-shell-v1", "unrelated"],
            delete: async (name) => { deleted.push(name); }
        },
        fetch: async () => { throw new Error("offline"); }
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(root, "sw.js"), "utf8"), context);
    const dispatch = async (name) => {
        let promise;
        handlers[name]({ waitUntil: (value) => { promise = value; } });
        await promise;
    };
    const request = async (url, method = "GET") => {
        let result;
        const pending = [];
        handlers.fetch({
            request: { url, method },
            respondWith: (value) => { result = value; },
            waitUntil: (value) => pending.push(value)
        });
        const response = await result;
        await Promise.all(pending);
        return response;
    };
    return { context, entries, deleted, dispatch, request };
}

test("install precaches existing shell; activate deletes obsolete app caches", async () => {
    const w = worker();
    await w.dispatch("install");
    await w.dispatch("activate");
    assert.deepEqual(w.deleted, ["pwa-radar-shell-v0", "pwa-radar-shell-v1"]);
});

test("API, cross-origin, POST and unknown resources bypass cache even offline", async () => {
    const w = worker();
    for (const url of [
        "https://pwaradar.it/api/v1/check-pwa?url=europa.eu",
        "https://other.example/index.html",
        "https://pwaradar.it/unknown"
    ]) assert.equal(await w.request(url), undefined);
    assert.equal(await w.request("https://pwaradar.it/", "POST"), undefined);
});

test("offline shell uses cache and never fabricates a successful response", async () => {
    const w = worker();
    w.entries.set("https://pwaradar.it/", "cached-shell");
    assert.equal(await w.request("https://pwaradar.it/"), "cached-shell");
    await assert.rejects(w.request("https://pwaradar.it/index.html"), /offline/);
});

test("online shell refreshes cache; HTTP errors remain visible", async () => {
    const w = worker();
    const response = { ok: true, type: "basic", clone: () => "fresh-shell" };
    w.context.fetch = async () => response;
    assert.equal(await w.request("https://pwaradar.it/"), response);
    assert.equal(w.entries.get("https://pwaradar.it/"), "fresh-shell");
    const errorResponse = { ok: false, status: 503 };
    w.context.fetch = async () => errorResponse;
    assert.equal(await w.request("https://pwaradar.it/"), errorResponse);
    assert.equal(w.entries.get("https://pwaradar.it/"), "fresh-shell");
});
