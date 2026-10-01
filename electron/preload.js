const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("localAgent", {
  restartTextWorker(modelId) {
    return ipcRenderer.invoke("local-agent:restart-text-worker", modelId);
  },
});
