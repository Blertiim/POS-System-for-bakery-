const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");

let mainWindow = null;
let backendProcess = null;

function getAppRoot() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
}

function getBackendCommand(port) {
  if (app.isPackaged) {
    return {
      command: path.join(process.resourcesPath, "backend", "bakery-pos-backend.exe"),
      args: ["--host", "127.0.0.1", "--port", String(port)],
      cwd: process.resourcesPath,
    };
  }

  return {
    command: process.platform === "win32" ? "python" : "python3",
    args: ["run.py", "--host", "127.0.0.1", "--port", String(port)],
    cwd: getAppRoot(),
  };
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

function waitForBackend(port, timeoutMs = 15000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(
        {
          hostname: "127.0.0.1",
          port,
          path: "/api/health",
          timeout: 1200,
        },
        (response) => {
          response.resume();
          if (response.statusCode === 200) {
            resolve();
            return;
          }
          retry();
        },
      );

      request.on("error", retry);
      request.on("timeout", () => {
        request.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error("Backend did not start in time."));
        return;
      }
      setTimeout(check, 300);
    };

    check();
  });
}

function startBackend(port) {
  const logPath = path.join(app.getPath("userData"), "backend.log");
  const logStream = fs.createWriteStream(logPath, { flags: "a" });
  const dbPath = path.join(app.getPath("userData"), "bakery_pos.db");
  const backend = getBackendCommand(port);

  backendProcess = spawn(backend.command, backend.args, {
    cwd: backend.cwd,
    env: {
      ...process.env,
      BAKERY_POS_DB: dbPath,
      BAKERY_POS_DESKTOP: "1",
    },
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  backendProcess.stdout.pipe(logStream);
  backendProcess.stderr.pipe(logStream);

  backendProcess.on("exit", (code) => {
    logStream.write(`\nBackend exited with code ${code}\n`);
  });
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 980,
    minHeight: 680,
    title: "FURRA LUMI POS",
    backgroundColor: "#f6f7f3",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadURL(`http://127.0.0.1:${port}`);
}

async function boot() {
  const port = await getFreePort();
  startBackend(port);

  try {
    await waitForBackend(port);
    createWindow(port);
  } catch (error) {
    dialog.showErrorBox(
      "FURRA LUMI POS",
      "Aplikacioni nuk mundi të nisej. Mbylleni dhe provojeni përsëri.",
    );
    app.quit();
  }
}

app.whenReady().then(boot);

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});

