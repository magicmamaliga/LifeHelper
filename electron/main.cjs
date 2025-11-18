const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let pythonProcess = null;

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  win.loadFile(path.join(__dirname, "..", "dist", "index.html"));

  // win.webContents.openDevTools(); // optional
}

function startPython() {
  const exePath = path.join(__dirname, "server.exe");
  pythonProcess = spawn(exePath, []);

  pythonProcess.stdout.on("data", data =>
    console.log("[PYTHON]", data.toString())
  );

  pythonProcess.stderr.on("data", data =>
    console.error("[PYTHON ERR]", data.toString())
  );

  pythonProcess.on("close", code =>
    console.log("Python closed with code:", code)
  );
}

app.whenReady().then(() => {
  startPython();
  createWindow();
});

app.on("window-all-closed", () => {
  // Kill python too
  if (pythonProcess) pythonProcess.kill();
  app.quit();
});
