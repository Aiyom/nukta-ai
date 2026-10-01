const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
let mainWindow;
let stackProcess;
let quitting = false;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForHealth(timeoutMs = 180000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch("http://127.0.0.1:8080/health");
      if (response.ok) return true;
    } catch (_) {
      // Stack still starting.
    }
    await sleep(1000);
  }
  return false;
}

function startStack(modelId) {
  const env = { ...process.env };
  if (modelId) env.MODEL = modelId;

  stackProcess = spawn("bash", ["scripts/run_stack.sh"], {
    cwd: rootDir,
    stdio: ["ignore", "pipe", "pipe"],
    env,
  });

  stackProcess.stdout.on("data", (data) => {
    console.log(`[stack] ${data.toString()}`);
  });
  stackProcess.stderr.on("data", (data) => {
    console.error(`[stack] ${data.toString()}`);
  });
  stackProcess.on("exit", (code) => {
    if (!quitting) {
      dialog.showErrorBox("Nukta AI stopped", `Backend stack exited with code ${code}.`);
    }
  });
}

async function stopStack() {
  quitting = true;
  if (stackProcess && !stackProcess.killed) {
    stackProcess.kill("SIGINT");
    await sleep(2500);
  }
  await new Promise((resolve) => {
    const stopper = spawn("bash", ["scripts/docker_stop.sh"], {
      cwd: rootDir,
      stdio: "ignore",
    });
    stopper.on("exit", resolve);
    stopper.on("error", resolve);
  });
}

async function restartStack(modelId) {
  quitting = true;
  if (stackProcess && !stackProcess.killed) {
    stackProcess.kill("SIGINT");
    await sleep(3500);
  }
  quitting = false;
  startStack(modelId);
  const ready = await waitForHealth(240000);
  if (!ready) {
    throw new Error("Local backend did not become ready after restart.");
  }
  if (mainWindow) {
    await mainWindow.loadURL("http://127.0.0.1:8080");
  }
  return { ok: true, model: modelId };
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1380,
    height: 900,
    minWidth: 980,
    minHeight: 680,
    title: "Nukta AI",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  await mainWindow.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(`
    <body style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; padding: 32px; background: #eef1f0; color: #142024">
      <h1>Nukta AI</h1>
      <p>Запускаю локальные модели, Docker API и рабочее пространство...</p>
    </body>
  `));

  startStack();
  const ready = await waitForHealth();
  if (!ready) {
    dialog.showErrorBox("Startup failed", "Local backend did not become ready in time. Check Docker Desktop and logs in .runtime/.");
    return;
  }
  await mainWindow.loadURL("http://127.0.0.1:8080");
}

app.whenReady().then(createWindow);

ipcMain.handle("local-agent:restart-text-worker", async (_, modelId) => {
  if (!modelId || typeof modelId !== "string") {
    throw new Error("Model ID is required.");
  }
  return restartStack(modelId);
});

app.on("before-quit", async (event) => {
  if (!quitting) {
    event.preventDefault();
    await stopStack();
    app.quit();
  }
});

app.on("window-all-closed", () => {
  app.quit();
});
