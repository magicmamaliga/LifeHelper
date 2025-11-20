const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let pyProcess = null;
let mainWindow = null;

// Start backend (PyInstaller EXE)
function startPythonBackend() {
  const exePath = path.join(process.resourcesPath, "backend", "lifehelper.exe");

  pyProcess = spawn(exePath, [], {
    cwd: path.dirname(exePath),
  });

  pyProcess.stdout.on("data", (data) => {
    console.log(`[PY] ${data}`);
  });

  pyProcess.stderr.on("data", (data) => {
    console.error(`[PY ERR] ${data}`);
  });

  pyProcess.on("close", (code) => {
    console.log(`Python backend exited with ${code}`);
  });
}

// Wait for backend to be ready
function waitForServer(url, attempts = 25) {
  const http = require("http");

  return new Promise((resolve, reject) => {
    const check = () => {
      http
        .get(url, () => resolve(true))
        .on("error", () => {
          if (attempts === 0) reject("Backend not responding");
          else {
            attempts--;
            setTimeout(check, 300);
          }
        });
    };
    check();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  waitForServer("http://127.0.0.1:8000")
    .then(() => {
      mainWindow.loadURL("http://127.0.0.1:8000");
    })
    .catch((err) => {
      console.error(err);
      mainWindow.loadURL("data:text/html,<h1>Backend failed</h1>");
    });
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  if (pyProcess) pyProcess.kill();
  if (process.platform !== "darwin") app.quit();
});
