const express = require("express");
const multer = require("multer");
const fs = require("fs");
const login = require("josh-fca");

const app = express();
const port = 8080;

app.use(express.urlencoded({ extended: true, limit: "10mb" }));
app.use(express.json({ limit: "10mb" }));
app.use(express.static("public"));

const upload = multer({ dest: "uploads/" });
const RECOVERY_FILE = "recovery.json";
const DEVICE_FILE = "device.json";
const activeTasks = {};
const loggedInUsers = {};

const fixedClientID = "royalheroz00112233";
const FALLBACK_UA = "Mozilla/5.0 (Linux; Android 10; SM-A107F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36";

// 💥 crash guard — server kabhi down nahi hoga
process.on("uncaughtException", (e) => console.error("💥 uncaughtException:", e));
process.on("unhandledRejection", (e) => console.error("💥 unhandledRejection:", e));

// josh-fca features ke liye config auto-create
if (!fs.existsSync("josh-fca.json")) {
  fs.writeFileSync("josh-fca.json", JSON.stringify({ BypassAutomationBehavior: true, AutoRefreshFbDtsg: true }, null, 2));
  console.log("✅ josh-fca.json created");
}

// 🔧 FIXED cookie parser — value ke andar "=" safe, URL-decode bhi
function parseCookies(raw) {
  const out = {};
  String(raw || "").split(";").forEach((part) => {
    part = part.trim();
    if (!part) return;
    const eq = part.indexOf("=");           // first "=" split
    if (eq === -1) return;
    const key = part.slice(0, eq).trim();
    let value = part.slice(eq + 1).trim();
    try { value = decodeURIComponent(value); } catch (e) {}
    if (key) out[key] = value;
  });
  return out;
}

function convertToAppState(cookies) {
  return Object.entries(cookies).map(([key, value]) => ({
    key,
    value,
    domain: "facebook.com",
    path: "/",
    secure: true,
    httpOnly: false,
  }));
}

function loadRecoveryData() {
  if (fs.existsSync(RECOVERY_FILE)) {
    try {
      const data = JSON.parse(fs.readFileSync(RECOVERY_FILE, "utf8"));
      if (Array.isArray(data.users)) return data.users;
    } catch (e) {
      console.error("❌ Failed to parse recovery file:", e);
    }
  }
  return [];
}

function saveRecoveryData(users) {
  fs.writeFileSync(RECOVERY_FILE, JSON.stringify({ users }, null, 2));
}

function updateUserProgress(uid, data) {
  const all = loadRecoveryData();
  const index = all.findIndex((u) => u.uid === uid);
  if (index >= 0) all[index] = { ...all[index], ...data };
  else all.push(data);
  saveRecoveryData(all);
}

function saveDeviceInfo(api) {
  const device = {
    clientID: api.clientID || fixedClientID,
    mqttClientID: api.mqttClientID || null,
    userAgent: api.userAgent || api?.ctx?.userAgent || FALLBACK_UA,
    ctx: api.ctx || {},
  };
  try {
    fs.writeFileSync(DEVICE_FILE, JSON.stringify(device, null, 2));
    console.log("✅ Device info saved");
  } catch (err) {
    console.log("❌ Failed to save device info:", err);
  }
}

function loadDeviceInfo() {
  if (fs.existsSync(DEVICE_FILE)) {
    try {
      const d = JSON.parse(fs.readFileSync(DEVICE_FILE, "utf8"));
      return {
        clientID: d.clientID || fixedClientID,
        mqttClientID: d.mqttClientID || null,
        ctx: d.ctx || {},
        userAgent: d.userAgent || FALLBACK_UA,
      };
    } catch (e) {}
  }
  return {};
}

function getLoginOptions(appState, deviceInfo) {
  return {
    appState,
    forceLogin: true,
    listenEvents: false,
    autoMarkDelivery: false,
    selfListen: false,
    updatePresence: false,
    logLevel: "silent",
    AutoReconnect: true,
    AutoRefreshFbDtsg: true,
    BypassAutomationBehavior: true,
    clientID: deviceInfo?.clientID || fixedClientID,
    mqttClientID: deviceInfo?.mqttClientID || null,
    userAgent: deviceInfo?.userAgent || FALLBACK_UA,
  };
}

// 🔑 LOGIN — ek bar mein, real error ke saath
app.post("/login-cookie", (req, res) => {
  const { cookies } = req.body;
  if (!cookies) return res.status(400).json({ success: false, error: "No cookies provided." });

  const parsedCookies = parseCookies(cookies);
  const appState = convertToAppState(parsedCookies);
  const deviceInfo = loadDeviceInfo();

  console.log("🔑 Cookies received:", Object.keys(parsedCookies).length, "| c_user:", parsedCookies.c_user || "MISSING ❌");

  try {
    login(getLoginOptions(appState, deviceInfo), (err, api) => {
      if (err) {
        console.error("❌ LOGIN ERROR:", JSON.stringify(err, null, 2));
        return res.json({
          success: false,
          error: err.errorSummary || err.message || "Login failed",
          detail: err,
        });
      }

      let uid = null;
      try { uid = api.getCurrentUserID(); } catch (e) {}
      if (!uid) uid = parsedCookies.c_user || null;  // fallback: cookie se

      if (!uid) return res.json({ success: false, error: "Could not get user ID (c_user missing/expired)" });

      saveDeviceInfo(api);
      loggedInUsers[uid] = { appState, currentIndex: 0 };
      console.log("✅ LOGGED IN AS:", uid);
      res.json({ success: true, uid });
    });
  } catch (e) {
    console.error("❌ CRASH in /login-cookie:", e);
    res.status(500).json({ success: false, error: e.message });
  }
});

// 📤 START
app.post("/start", upload.single("messages"), (req, res) => {
  const { delay, hatersName, targetUid } = req.body;
  if (!req.file || !delay || !hatersName || !targetUid) {
    return res.status(400).send("❌ Missing required fields.");
  }

  const filePath = req.file.path;
  const rawMessages = fs.readFileSync(filePath, "utf8");
  const messages = rawMessages.split("\n").filter(Boolean);
  fs.unlink(filePath, () => {}); // cleanup

  const ids = Object.keys(loggedInUsers);
  if (ids.length === 0) return res.status(400).send("❌ Pehle cookie se login karo.");

  for (const uid of ids) {
    startProcess(loggedInUsers[uid].appState, uid, messages, parseInt(delay), hatersName, targetUid, 1, loggedInUsers[uid].currentIndex || 0);
  }

  res.send(`✅ Started sending to ${targetUid} from ${ids.length} ID(s)`);
});

function startProcess(appState, uid, messages, delay, hatersName, targetUid, attempt = 1, index = 0) {
  if (activeTasks[uid]) return;
  const deviceInfo = loadDeviceInfo();

  login(getLoginOptions(appState, deviceInfo), (err, api) => {
    if (err) {
      if (attempt < 2) {
        console.log(`[${uid}] Login failed, retry (${attempt + 1}/2)...`);
        return setTimeout(() => startProcess(appState, uid, messages, delay, hatersName, targetUid, attempt + 1, index), 3000);
      }
      console.log(`[${uid}] ❌ Login failed twice. Removing...`);
      delete activeTasks[uid];
      delete loggedInUsers[uid];
      saveRecoveryData(loadRecoveryData().filter((u) => u.uid !== uid));
      return;
    }

    saveDeviceInfo(api);
    activeTasks[uid] = true;
    if (!loggedInUsers[uid]) loggedInUsers[uid] = { appState, currentIndex: index };

    function sendLoop() {
      if (!activeTasks[uid]) return;
      const msg = `${hatersName} ${messages[index]}`;

      api.sendMessage(msg, targetUid, (err2) => {
        if (err2) {
          console.log(`[${uid}] ❌ Message failed:`, err2);
          delete activeTasks[uid];
          delete loggedInUsers[uid];
          saveRecoveryData(loadRecoveryData().filter((u) => u.uid !== uid));
          return;
        }

        console.log(`[${uid}] ✅ Sent: ${msg}`);
        index = (index + 1) % messages.length;
        if (loggedInUsers[uid]) loggedInUsers[uid].currentIndex = index;

        updateUserProgress(uid, {
          uid,
          cookies: appState.map((c) => `${c.key}=${c.value}`).join("; "),
          delay,
          hatersName,
          targetUid,
          messages,
          currentIndex: index,
        });

        setTimeout(sendLoop, delay * 1000);
      });
    }

    sendLoop();
  });
}

// 🛑 STOP
app.post("/stop", (req, res) => {
  const { uid } = req.body;
  if (activeTasks[uid]) {
    delete activeTasks[uid];
    saveRecoveryData(loadRecoveryData().filter((u) => u.uid !== uid));
    res.send(`🛑 Stopped task for ID: ${uid}`);
  } else {
    res.send(`⚠️ No task found for ID: ${uid}`);
  }
});

// 🔄 RESUME
async function resumeAllProcesses() {
  const users = loadRecoveryData();
  const deviceInfo = loadDeviceInfo();

  for (const u of users) {
    await new Promise((r) => setTimeout(r, 2000));
    const appState = convertToAppState(parseCookies(u.cookies));

    login(getLoginOptions(appState, deviceInfo), (err, api) => {
      if (err) {
        console.log(`[${u.uid}] Resume failed, retry...`);
        return setTimeout(() => {
          login(getLoginOptions(appState, deviceInfo), (err2, api2) => {
            if (err2) {
              console.log(`[${u.uid}] ❌ Resume failed twice. Removing.`);
              delete loggedInUsers[u.uid];
              saveRecoveryData(loadRecoveryData().filter((x) => x.uid !== u.uid));
            } else {
              saveDeviceInfo(api2);
              loggedInUsers[u.uid] = { appState, currentIndex: u.currentIndex || 0 };
              startProcess(appState, u.uid, u.messages, u.delay, u.hatersName, u.targetUid, 1, u.currentIndex);
            }
          });
        }, 3000);
      } else {
        saveDeviceInfo(api);
        loggedInUsers[u.uid] = { appState, currentIndex: u.currentIndex || 0 };
        startProcess(appState, u.uid, u.messages, u.delay, u.hatersName, u.targetUid, 1, u.currentIndex);
      }
    });
  }
}

// ✅ STATUS
app.get("/status", (req, res) => {
  res.json({
    loggedIn: Object.keys(loggedInUsers),
    activeTasks: Object.keys(activeTasks),
  });
});

app.listen(port, () => {
  console.log(`🚀 Server running at http://localhost:${port}`);
  resumeAllProcesses();
});
