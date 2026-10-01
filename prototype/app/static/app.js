const views = {
  agent: document.querySelector("#agentView"),
  search: document.querySelector("#searchView"),
  images: document.querySelector("#imagesView"),
  sites: document.querySelector("#sitesView"),
  models: document.querySelector("#modelsView"),
  artifacts: document.querySelector("#artifactsView"),
};
const title = document.querySelector("#viewTitle");
const conversation = document.querySelector("#conversation");
const agentForm = document.querySelector("#agentForm");
const searchForm = document.querySelector("#searchForm");
const webAskForm = document.querySelector("#webAskForm");
const promptInput = document.querySelector("#prompt");
const searchQuery = document.querySelector("#searchQuery");
const searchResults = document.querySelector("#searchResults");
const webContext = document.querySelector("#webContext");
const webTitle = document.querySelector("#webTitle");
const webUrl = document.querySelector("#webUrl");
const webQuestion = document.querySelector("#webQuestion");
const webAnswer = document.querySelector("#webAnswer");
const siteForm = document.querySelector("#siteForm");
const imageForm = document.querySelector("#imageForm");
const siteName = document.querySelector("#siteName");
const sitePrompt = document.querySelector("#sitePrompt");
const imagePrompt = document.querySelector("#imagePrompt");
const siteResult = document.querySelector("#siteResult");
const imageResult = document.querySelector("#imageResult");
const textModelSelect = document.querySelector("#textModelSelect");
const imageModelSelect = document.querySelector("#imageModelSelect");
const applyModelsButton = document.querySelector("#applyModelsButton");
const restartTextWorkerButton = document.querySelector("#restartTextWorkerButton");
const modelSwitchStatus = document.querySelector("#modelSwitchStatus");
const modelAddForm = document.querySelector("#modelAddForm");
const newModelKind = document.querySelector("#newModelKind");
const newModelId = document.querySelector("#newModelId");
const newModelUrl = document.querySelector("#newModelUrl");
const newModelLicense = document.querySelector("#newModelLicense");
const modelCatalog = document.querySelector("#modelCatalog");
const runButton = document.querySelector("#runButton");
const benchButton = document.querySelector("#benchButton");
const clearButton = document.querySelector("#clearButton");
const systemFacts = document.querySelector("#systemFacts");
const stepList = document.querySelector("#stepList");
const taskList = document.querySelector("#taskList");
const artifactList = document.querySelector("#artifactList");

let tasks = [];
let selectedPage = null;
let modelState = null;

const maxComposerRows = 5;

function resizeComposerInput(input) {
  if (!input) return;
  const styles = window.getComputedStyle(input);
  const lineHeight = Number.parseFloat(styles.lineHeight) || 22;
  const padding =
    Number.parseFloat(styles.paddingTop || "0") + Number.parseFloat(styles.paddingBottom || "0");
  const maxHeight = Math.ceil(lineHeight * maxComposerRows + padding);
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
  input.style.overflowY = input.scrollHeight > maxHeight ? "auto" : "hidden";
}

function resetComposerInput(input) {
  if (!input) return;
  input.value = "";
  resizeComposerInput(input);
}

document.querySelectorAll("textarea.auto-grow").forEach((input) => {
  resizeComposerInput(input);
  input.addEventListener("input", () => resizeComposerInput(input));
  input.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    input.form?.requestSubmit();
  });
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    Object.values(views).forEach((view) => view.classList.remove("active"));
    views[button.dataset.view].classList.add("active");
    title.textContent = {
      agent: "Полноценный локальный агент",
      search: "Поиск и разговор по сайту",
      images: "Локальная генерация картинок",
      sites: "Генератор локальных сайтов",
      models: "Настройки моделей",
      artifacts: "Артефакты сессии",
    }[button.dataset.view];
    document.querySelectorAll("textarea.auto-grow").forEach(resizeComposerInput);
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
    <div><dt>Image model</dt><dd>${health.image_model}</dd></div>
  `;
}

function modelOption(model) {
  const option = document.createElement("option");
  option.value = model.id;
  option.textContent = `${model.name || model.id} (${model.backend})`;
  option.selected = Boolean(model.active);
  return option;
}

function renderModelSelect(select, models) {
  select.innerHTML = "";
  for (const model of models || []) {
    select.appendChild(modelOption(model));
  }
}

function renderModelCatalog() {
  modelCatalog.innerHTML = "";
  const groups = [
    ["text", "Текстовые модели"],
    ["image", "Модели картинок"],
    ["video", "Видео модели"],
  ];
  for (const [kind, label] of groups) {
    const section = document.createElement("section");
    section.className = "model-group";
    section.innerHTML = `<h3>${label}</h3>`;
    const models = modelState?.models?.[kind] || [];
    if (!models.length) {
      section.insertAdjacentHTML("beforeend", "<p>Пока нет моделей.</p>");
    }
    for (const model of models) {
      const card = document.createElement("article");
      card.className = `model-card${model.active ? " active" : ""}`;
      card.innerHTML = `
        <div>
          <h4></h4>
          <p class="model-id"></p>
        </div>
        <dl>
          <div><dt>Backend</dt><dd></dd></div>
          <div><dt>Лицензия</dt><dd></dd></div>
          <div><dt>Статус</dt><dd></dd></div>
        </dl>
        <p class="model-notes"></p>
        <a target="_blank" rel="noreferrer">Model card</a>
        <code></code>
      `;
      card.querySelector("h4").textContent = model.name || model.id;
      card.querySelector(".model-id").textContent = model.id;
      card.querySelectorAll("dd")[0].textContent = model.backend || "unknown";
      card.querySelectorAll("dd")[1].textContent = model.license || "Проверь upstream model card";
      card.querySelectorAll("dd")[2].textContent = model.installed ? "установлена" : "можно скачать";
      card.querySelector(".model-notes").textContent = model.notes || "";
      const link = card.querySelector("a");
      if (model.source_url) {
        link.href = model.source_url;
      } else {
        link.remove();
      }
      card.querySelector("code").textContent = model.download_command || "";
      section.appendChild(card);
    }
    modelCatalog.appendChild(section);
  }
}

async function refreshModels() {
  const response = await fetch("/v1/models");
  modelState = await readJsonOrThrow(response);
  renderModelSelect(textModelSelect, modelState.models.text);
  renderModelSelect(imageModelSelect, modelState.models.image);
  renderModelCatalog();
}

async function switchModel(kind, modelId) {
  const response = await fetch("/v1/models/active", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ kind, model_id: modelId }),
  });
  return readJsonOrThrow(response);
}

agentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = promptInput.value.trim();
  if (!input) return;
  resetComposerInput(promptInput);
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

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = searchQuery.value.trim();
  if (!query) return;
  resetComposerInput(searchQuery);
  searchResults.textContent = "Ищу...";
  webContext.hidden = true;
  selectedPage = null;
  try {
    const response = await fetch("/v1/search", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query, max_results: 6 }),
    });
    const data = await readJsonOrThrow(response);
    searchResults.innerHTML = "";
    if (!data.results.length) {
      searchResults.textContent = "Ничего не найдено.";
      return;
    }
    for (const result of data.results) {
      const card = document.createElement("article");
      card.className = "search-card";
      card.innerHTML = `
        <h3></h3>
        <p class="search-url"></p>
        <p class="search-snippet"></p>
        <button type="button">Читать и продолжить беседу</button>
      `;
      card.querySelector("h3").textContent = result.title;
      card.querySelector(".search-url").textContent = result.url;
      card.querySelector(".search-snippet").textContent = result.snippet || "Без описания";
      card.querySelector("button").addEventListener("click", () => openSearchResult(result));
      searchResults.appendChild(card);
    }
  } catch (error) {
    searchResults.textContent = `Ошибка поиска: ${error.message}`;
  }
});

async function openSearchResult(result) {
  webContext.hidden = false;
  webTitle.textContent = "Читаю страницу...";
  webUrl.textContent = result.url;
  webAnswer.textContent = "";
  try {
    const response = await fetch("/v1/web/page", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: result.url }),
    });
    selectedPage = await readJsonOrThrow(response);
    webTitle.textContent = selectedPage.title;
    webUrl.textContent = selectedPage.url;
    webAnswer.textContent = `Страница прочитана: ${selectedPage.text.length} символов. Теперь можно спрашивать по этому сайту.`;
  } catch (error) {
    webAnswer.textContent = `Не удалось прочитать страницу: ${error.message}`;
  }
}

webAskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedPage) {
    webAnswer.textContent = "Сначала выбери сайт из результатов поиска.";
    return;
  }
  const question = webQuestion.value.trim();
  if (!question) return;
  resetComposerInput(webQuestion);
  webAnswer.textContent = "Думаю по выбранной странице...";
  try {
    const response = await fetch("/v1/web/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        url: selectedPage.url,
        title: selectedPage.title,
        page_text: selectedPage.text,
        question,
      }),
    });
    const data = await readJsonOrThrow(response);
    webAnswer.textContent = data.answer;
  } catch (error) {
    webAnswer.textContent = `Ошибка ответа по сайту: ${error.message}`;
  }
});

imageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = imagePrompt.value.trim();
  if (!input) return;
  resetComposerInput(imagePrompt);
  imageResult.textContent = "Генерирую локально...";
  const beforeCount = artifactList.children.length;
  await runAgent(input, "image");
  imageResult.innerHTML = "<p>Готово. Результат добавлен в ленту агента и в Артефакты.</p>";
  if (artifactList.children.length === beforeCount) {
    imageResult.innerHTML = "<p>Генерация завершилась, но артефакт не вернулся. Проверь ход выполнения справа.</p>";
  }
});

applyModelsButton.addEventListener("click", async () => {
  applyModelsButton.disabled = true;
  modelSwitchStatus.textContent = "Применяю...";
  try {
    await switchModel("text", textModelSelect.value);
    await switchModel("image", imageModelSelect.value);
    modelSwitchStatus.textContent = "Готово. Для single-model MLX перезапусти worker с выбранным Model ID.";
    await refreshModels();
    await refreshHealth();
  } catch (error) {
    modelSwitchStatus.textContent = `Ошибка: ${error.message}`;
  } finally {
    applyModelsButton.disabled = false;
  }
});

restartTextWorkerButton.addEventListener("click", async () => {
  const modelId = textModelSelect.value;
  restartTextWorkerButton.disabled = true;
  applyModelsButton.disabled = true;
  try {
    await switchModel("text", modelId);
    if (window.localAgent?.restartTextWorker) {
      modelSwitchStatus.textContent = `Перезапускаю локальный text worker: ${modelId}`;
      await window.localAgent.restartTextWorker(modelId);
      modelSwitchStatus.textContent = "Готово. Worker перезапущен, UI обновлен.";
      await refreshModels();
      await refreshHealth();
      return;
    }
    modelSwitchStatus.innerHTML = `
      <span>В обычном браузере нельзя управлять процессами Mac. Запусти через Mac app или выполни:</span>
      <code>MODEL="${modelId}" bash scripts/run_stack.sh</code>
    `;
  } catch (error) {
    modelSwitchStatus.textContent = `Ошибка перезапуска: ${error.message}`;
  } finally {
    restartTextWorkerButton.disabled = false;
    applyModelsButton.disabled = false;
  }
});

modelAddForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = newModelId.value.trim();
  if (!id) return;
  modelSwitchStatus.textContent = "Добавляю модель...";
  try {
    const response = await fetch("/v1/models", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        id,
        name: id.split("/").at(-1),
        kind: newModelKind.value,
        source_url: newModelUrl.value.trim(),
        license: newModelLicense.value.trim(),
        notes: "Пользовательская модель. Проверь лицензию, требования VRAM/RAM и формат перед production.",
      }),
    });
    await readJsonOrThrow(response);
    newModelId.value = "";
    newModelUrl.value = "";
    newModelLicense.value = "";
    modelSwitchStatus.textContent = "Модель добавлена в каталог.";
    await refreshModels();
  } catch (error) {
    modelSwitchStatus.textContent = `Ошибка: ${error.message}`;
  }
});

refreshHealth().catch(() => {
  systemFacts.innerHTML = "<div><dt>Статус</dt><dd>Недоступен</dd></div>";
});
refreshModels().catch(() => {
  modelCatalog.textContent = "Каталог моделей недоступен.";
});
