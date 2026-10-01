const views = {
  agent: document.querySelector("#agentView"),
  images: document.querySelector("#imagesView"),
  sites: document.querySelector("#sitesView"),
  artifacts: document.querySelector("#artifactsView"),
};
const title = document.querySelector("#viewTitle");
const conversation = document.querySelector("#conversation");
const agentForm = document.querySelector("#agentForm");
const promptInput = document.querySelector("#prompt");
const siteForm = document.querySelector("#siteForm");
const imageForm = document.querySelector("#imageForm");
const siteName = document.querySelector("#siteName");
const sitePrompt = document.querySelector("#sitePrompt");
const imagePrompt = document.querySelector("#imagePrompt");
const siteResult = document.querySelector("#siteResult");
const imageResult = document.querySelector("#imageResult");
const runButton = document.querySelector("#runButton");
const benchButton = document.querySelector("#benchButton");
const clearButton = document.querySelector("#clearButton");
const systemFacts = document.querySelector("#systemFacts");
const stepList = document.querySelector("#stepList");
const taskList = document.querySelector("#taskList");
const artifactList = document.querySelector("#artifactList");

let tasks = [];

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    Object.values(views).forEach((view) => view.classList.remove("active"));
    views[button.dataset.view].classList.add("active");
    title.textContent = {
      agent: "Полноценный локальный агент",
      images: "Локальная генерация картинок",
      sites: "Генератор локальных сайтов",
      artifacts: "Артефакты сессии",
    }[button.dataset.view];
  });
});

async function readJsonOrThrow(response) {
  const raw = await response.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(raw || response.statusText);
  }
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

function addBubble(role, content, meta = "") {
  conversation.querySelector(".empty-state")?.remove();
  const item = document.createElement("article");
  item.className = `bubble ${role}`;
  item.innerHTML = `<div class="bubble-text"></div>${meta ? `<div class="bubble-meta"></div>` : ""}`;
  item.querySelector(".bubble-text").textContent = content;
  if (meta) item.querySelector(".bubble-meta").textContent = meta;
  conversation.appendChild(item);
  conversation.scrollTop = conversation.scrollHeight;
  return item;
}

function renderSteps(steps) {
  stepList.innerHTML = "";
  for (const step of steps || []) {
    const item = document.createElement("li");
    item.className = step.status;
    item.innerHTML = `<strong>${step.title}</strong><span>${step.detail}</span>`;
    stepList.appendChild(item);
  }
}

function renderTasks() {
  taskList.innerHTML = "";
  for (const task of tasks.slice(0, 10)) {
    const item = document.createElement("div");
    item.className = "task-item";
    item.innerHTML = `<strong>${task.mode}</strong><span>${task.title}</span>`;
    taskList.appendChild(item);
  }
}

function addArtifactCard(kind, body) {
  const card = document.createElement("article");
  card.className = "artifact-card";
  card.appendChild(body);
  artifactList.prepend(card);
  return card;
}

function renderArtifacts(artifacts, mode) {
  for (const artifact of artifacts || []) {
    if (artifact.url) {
      const wrap = document.createElement("div");
      wrap.innerHTML = `<img alt="Generated image" src="${artifact.url}"><p>${artifact.model || mode}; ${artifact.latency_seconds || "?"}s</p>`;
      addArtifactCard("image", wrap);
      const bubble = addBubble("assistant", "Изображение готово", `${artifact.model || mode}; ${artifact.latency_seconds || "?"}s`);
      const image = document.createElement("img");
      image.src = artifact.url;
      image.alt = "Generated image";
      bubble.appendChild(image);
    }
    if (artifact.json) {
      const pre = document.createElement("pre");
      pre.textContent = artifact.json;
      addArtifactCard("json", pre);
    }
  }
}

async function runAgent(input, mode = "auto") {
  addBubble("user", input, mode);
  const progress = addBubble("assistant", "Выполняю локально...", "agent running");
  runButton.disabled = true;
  benchButton.disabled = true;
  try {
    const response = await fetch("/v1/agent/runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ input, mode }),
    });
    const result = await readJsonOrThrow(response);
    progress.remove();
    renderSteps(result.steps);
    tasks.unshift({ title: input, mode: result.mode });
    renderTasks();
    if (result.mode !== "image") {
      addBubble("assistant", result.message || "Готово", result.status);
    }
    renderArtifacts(result.artifacts, result.mode);
  } catch (error) {
    progress.remove();
    addBubble("assistant", `Ошибка: ${error.message}`, "failed");
  } finally {
    runButton.disabled = false;
    benchButton.disabled = false;
  }
}

async function refreshHealth() {
  const response = await fetch("/health");
  const health = await response.json();
  systemFacts.innerHTML = `
    <div><dt>Режим</dt><dd>${health.environment}</dd></div>
    <div><dt>Текст</dt><dd>${health.text_backend}</dd></div>
    <div><dt>Text model</dt><dd>${health.text_model}</dd></div>
    <div><dt>Image</dt><dd>${health.image_backend}</dd></div>
  `;
}

agentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = promptInput.value.trim();
  if (!input) return;
  promptInput.value = "";
  await runAgent(input);
});

benchButton.addEventListener("click", () => runAgent("Замерь скорость локальной модели", "benchmark"));

clearButton.addEventListener("click", () => {
  conversation.innerHTML = `<article class="empty-state"><h3>Дай задачу обычным языком</h3><p>Например: “сгенерируй картинку дерево в пустыне”, “напиши код”, “замерь скорость”.</p></article>`;
  stepList.innerHTML = "";
});

siteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  siteResult.textContent = "Создаю сайт локально...";
  try {
    const response = await fetch("/v1/sites/generate", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name: siteName.value.trim(), prompt: sitePrompt.value.trim() }),
    });
    const site = await readJsonOrThrow(response);
    siteResult.innerHTML = `
      <article class="site-card">
        <h3>${site.id}</h3>
        <p>${site.path}</p>
        <a href="${site.url}" target="_blank">Открыть preview</a>
        <iframe src="${site.url}" title="Site preview"></iframe>
      </article>
    `;
    const link = document.createElement("div");
    link.innerHTML = `<h3>${site.id}</h3><p>${site.path}</p><a href="${site.url}" target="_blank">Preview</a>`;
    addArtifactCard("site", link);
  } catch (error) {
    siteResult.textContent = `Ошибка: ${error.message}`;
  }
});

imageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = imagePrompt.value.trim();
  if (!input) return;
  imageResult.textContent = "Генерирую локально...";
  const beforeCount = artifactList.children.length;
  await runAgent(input, "image");
  imageResult.innerHTML = "<p>Готово. Результат добавлен в ленту агента и в Артефакты.</p>";
  if (artifactList.children.length === beforeCount) {
    imageResult.innerHTML = "<p>Генерация завершилась, но артефакт не вернулся. Проверь ход выполнения справа.</p>";
  }
});

refreshHealth().catch(() => {
  systemFacts.innerHTML = "<div><dt>Статус</dt><dd>Недоступен</dd></div>";
});
