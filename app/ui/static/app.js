const templateSelect = document.getElementById("templateSelect");
const templateInfo = document.getElementById("templateInfo");
const messageBox = document.getElementById("messageBox");
const pageRuleEditor = document.getElementById("pageRuleEditor");
const groupRuleEditor = document.getElementById("groupRuleEditor");

const uploadTemplateForm = document.getElementById("uploadTemplateForm");
const createJobForm = document.getElementById("createJobForm");
const rulesForm = document.getElementById("rulesForm");

const reloadTemplatesBtn = document.getElementById("reloadTemplatesBtn");
const resetDefaultBtn = document.getElementById("resetDefaultBtn");

const jobStatus = document.getElementById("jobStatus");
const jobIdText = document.getElementById("jobIdText");
const jobStateText = document.getElementById("jobStateText");
const jobProgressText = document.getElementById("jobProgressText");
const jobWarningText = document.getElementById("jobWarningText");
const jobErrorText = document.getElementById("jobErrorText");
const downloadLink = document.getElementById("downloadLink");

const GROUP_KEYS = [
  "cover",
  "front_matter",
  "chapter_title",
  "section_title",
  "subsection_title",
  "body",
  "figure_caption",
  "table_caption",
  "toc",
];

const PAGE_FIELDS = [
  "page_width_pt",
  "page_height_pt",
  "margin_top_pt",
  "margin_bottom_pt",
  "margin_left_pt",
  "margin_right_pt",
  "header_distance_pt",
  "footer_distance_pt",
  "gutter_pt",
  "page_number_start",
];

let templates = [];
let currentTemplateId = null;
let currentRules = null;
let pollTimer = null;

function setMessage(message) {
  messageBox.textContent = `[${new Date().toLocaleTimeString()}] ${message}\n${messageBox.textContent}`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || JSON.stringify(payload);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return response.json();
}

function renderTemplateSelect() {
  templateSelect.innerHTML = "";

  for (const template of templates) {
    const option = document.createElement("option");
    option.value = template.id;
    option.textContent = `${template.name}${template.is_default ? " (default)" : ""}`;
    templateSelect.appendChild(option);
  }

  if (!currentTemplateId && templates.length > 0) {
    const defaultTemplate = templates.find((t) => t.is_default) || templates[0];
    currentTemplateId = defaultTemplate.id;
  }

  if (currentTemplateId) {
    templateSelect.value = currentTemplateId;
  }
}

function createNumberInput(name, value, step = "0.1") {
  const wrapper = document.createElement("label");
  wrapper.className = "field";
  wrapper.innerHTML = `<span>${name}</span>`;

  const input = document.createElement("input");
  input.type = "number";
  input.name = name;
  input.step = step;
  input.value = value;
  wrapper.appendChild(input);

  return wrapper;
}

function createTextInput(name, value) {
  const wrapper = document.createElement("label");
  wrapper.className = "field";
  wrapper.innerHTML = `<span>${name}</span>`;

  const input = document.createElement("input");
  input.type = "text";
  input.name = name;
  input.value = value;
  wrapper.appendChild(input);

  return wrapper;
}

function createCheckboxInput(name, checked) {
  const wrapper = document.createElement("label");
  wrapper.className = "field checkbox-field";

  const input = document.createElement("input");
  input.type = "checkbox";
  input.name = name;
  input.checked = checked;

  const span = document.createElement("span");
  span.textContent = name;

  wrapper.appendChild(input);
  wrapper.appendChild(span);
  return wrapper;
}

function renderRuleEditor() {
  if (!currentRules) {
    return;
  }

  pageRuleEditor.innerHTML = "";
  groupRuleEditor.innerHTML = "";

  for (const field of PAGE_FIELDS) {
    const step = field.endsWith("start") ? "1" : "0.1";
    pageRuleEditor.appendChild(createNumberInput(`page.${field}`, currentRules.page[field], step));
  }

  const pageFormat = document.createElement("label");
  pageFormat.className = "field";
  pageFormat.innerHTML = "<span>page.page_number_format</span>";
  const formatSelect = document.createElement("select");
  formatSelect.name = "page.page_number_format";
  ["decimal", "upperRoman", "lowerRoman", "none"].forEach((item) => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    option.selected = currentRules.page.page_number_format === item;
    formatSelect.appendChild(option);
  });
  pageFormat.appendChild(formatSelect);
  pageRuleEditor.appendChild(pageFormat);

  for (const groupKey of GROUP_KEYS) {
    const rule = currentRules.groups[groupKey];

    const card = document.createElement("div");
    card.className = "group-card";

    const title = document.createElement("h4");
    title.textContent = groupKey;
    card.appendChild(title);

    card.appendChild(createTextInput(`${groupKey}.font_name`, rule.font_name));
    card.appendChild(createNumberInput(`${groupKey}.font_size_pt`, rule.font_size_pt));
    card.appendChild(createTextInput(`${groupKey}.alignment`, rule.alignment));
    card.appendChild(createNumberInput(`${groupKey}.line_spacing`, rule.line_spacing, "0.05"));
    card.appendChild(createNumberInput(`${groupKey}.space_before_pt`, rule.space_before_pt));
    card.appendChild(createNumberInput(`${groupKey}.space_after_pt`, rule.space_after_pt));
    card.appendChild(createNumberInput(`${groupKey}.first_line_indent_pt`, rule.first_line_indent_pt));
    card.appendChild(createCheckboxInput(`${groupKey}.bold`, rule.bold));
    card.appendChild(createCheckboxInput(`${groupKey}.italic`, rule.italic));

    groupRuleEditor.appendChild(card);
  }

  templateInfo.textContent = JSON.stringify(currentRules, null, 2);
}

function collectRulesFromEditor() {
  const rules = structuredClone(currentRules);

  PAGE_FIELDS.forEach((field) => {
    const input = rulesForm.elements.namedItem(`page.${field}`);
    if (input) {
      rules.page[field] = Number(input.value);
    }
  });

  const formatSelect = rulesForm.elements.namedItem("page.page_number_format");
  if (formatSelect) {
    rules.page.page_number_format = formatSelect.value;
  }

  for (const groupKey of GROUP_KEYS) {
    const group = rules.groups[groupKey];
    if (!group) continue;

    const fontName = rulesForm.elements.namedItem(`${groupKey}.font_name`);
    const fontSize = rulesForm.elements.namedItem(`${groupKey}.font_size_pt`);
    const alignment = rulesForm.elements.namedItem(`${groupKey}.alignment`);
    const lineSpacing = rulesForm.elements.namedItem(`${groupKey}.line_spacing`);
    const before = rulesForm.elements.namedItem(`${groupKey}.space_before_pt`);
    const after = rulesForm.elements.namedItem(`${groupKey}.space_after_pt`);
    const indent = rulesForm.elements.namedItem(`${groupKey}.first_line_indent_pt`);
    const bold = rulesForm.elements.namedItem(`${groupKey}.bold`);
    const italic = rulesForm.elements.namedItem(`${groupKey}.italic`);

    group.font_name = fontName.value;
    group.font_size_pt = Number(fontSize.value);
    group.alignment = alignment.value;
    group.line_spacing = Number(lineSpacing.value);
    group.space_before_pt = Number(before.value);
    group.space_after_pt = Number(after.value);
    group.first_line_indent_pt = Number(indent.value);
    group.bold = Boolean(bold.checked);
    group.italic = Boolean(italic.checked);
  }

  return rules;
}

async function refreshTemplates() {
  templates = await requestJson("/api/templates");
  renderTemplateSelect();
  if (currentTemplateId) {
    await loadTemplateRules(currentTemplateId);
  }
}

async function loadTemplateRules(templateId) {
  const result = await requestJson(`/api/templates/${templateId}/rules`);
  currentRules = result.rules;
  currentTemplateId = result.id;
  renderRuleEditor();
  setMessage(`Template loaded: ${result.name}`);
}

function renderJobStatus(payload) {
  jobStatus.classList.remove("hidden");
  jobIdText.textContent = payload.job_id;
  jobStateText.textContent = payload.status;
  jobProgressText.textContent = payload.progress;
  jobWarningText.textContent = payload.warning_message || "-";
  jobErrorText.textContent = payload.error_message || "-";

  if (payload.download_url) {
    downloadLink.classList.remove("hidden");
    downloadLink.href = payload.download_url;
  } else {
    downloadLink.classList.add("hidden");
    downloadLink.href = "#";
  }
}

async function pollJob(jobId) {
  try {
    const payload = await requestJson(`/api/jobs/${jobId}`);
    renderJobStatus(payload);

    if (payload.status === "success" || payload.status === "failed") {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      setMessage(`Job ${jobId} finished with status ${payload.status}`);
    }
  } catch (error) {
    setMessage(`Job polling failed: ${error.message}`);
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }
}

async function init() {
  try {
    templates = Array.isArray(window.__BOOTSTRAP_TEMPLATES__) ? window.__BOOTSTRAP_TEMPLATES__ : [];
    renderTemplateSelect();

    if (templates.length === 0) {
      setMessage("No templates found, resetting default template...");
      const reset = await requestJson("/api/templates/default/reset", { method: "POST" });
      currentRules = reset.rules;
      currentTemplateId = reset.id;
      await refreshTemplates();
    } else {
      await loadTemplateRules(currentTemplateId || templates[0].id);
    }
  } catch (error) {
    setMessage(`Initialization failed: ${error.message}`);
  }
}

reloadTemplatesBtn.addEventListener("click", async () => {
  try {
    await refreshTemplates();
    setMessage("Templates reloaded.");
  } catch (error) {
    setMessage(`Reload failed: ${error.message}`);
  }
});

resetDefaultBtn.addEventListener("click", async () => {
  try {
    const response = await requestJson("/api/templates/default/reset", { method: "POST" });
    currentTemplateId = response.id;
    currentRules = response.rules;
    await refreshTemplates();
    setMessage("Default template reset successfully.");
  } catch (error) {
    setMessage(`Reset failed: ${error.message}`);
  }
});

templateSelect.addEventListener("change", async () => {
  try {
    currentTemplateId = templateSelect.value;
    await loadTemplateRules(currentTemplateId);
  } catch (error) {
    setMessage(`Failed to load selected template: ${error.message}`);
  }
});

uploadTemplateForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  try {
    const formData = new FormData(uploadTemplateForm);
    const response = await fetch("/api/templates/upload", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Template upload failed.");
    }

    const payload = await response.json();
    currentTemplateId = payload.id;
    currentRules = payload.rules;

    await refreshTemplates();
    templateSelect.value = currentTemplateId;
    setMessage(`Template uploaded: ${payload.name}`);
    uploadTemplateForm.reset();
  } catch (error) {
    setMessage(`Upload template failed: ${error.message}`);
  }
});

rulesForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!currentTemplateId || !currentRules) {
    setMessage("No active template to save rules.");
    return;
  }

  try {
    const editedRules = collectRulesFromEditor();
    const payload = await requestJson(`/api/templates/${currentTemplateId}/rules`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(editedRules),
    });

    currentRules = payload.rules;
    renderRuleEditor();
    setMessage("Template rules saved.");
  } catch (error) {
    setMessage(`Save rules failed: ${error.message}`);
  }
});

createJobForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!currentTemplateId || !currentRules) {
    setMessage("Please load a template first.");
    return;
  }

  try {
    const editedRules = collectRulesFromEditor();

    const formData = new FormData(createJobForm);
    formData.append("template_id", currentTemplateId);
    formData.append("rules_override", JSON.stringify(editedRules));

    const response = await fetch("/api/jobs", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Create job failed.");
    }

    const payload = await response.json();
    renderJobStatus({
      job_id: payload.job_id,
      status: payload.status,
      progress: payload.progress,
      warning_message: null,
      error_message: null,
      download_url: null,
    });

    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    pollTimer = setInterval(() => pollJob(payload.job_id), 1500);
    await pollJob(payload.job_id);

    setMessage(`Job created: ${payload.job_id}`);
  } catch (error) {
    setMessage(`Create job failed: ${error.message}`);
  }
});

init();
