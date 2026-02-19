const DEFAULT_API_URL = "http://localhost:8000";
const MAX_TEXT_CHARS = 50000;
const MIN_TEXT_CHARS = 50;
const extApi = globalThis.browser ?? globalThis.chrome;

const dom = {
  apiUrl: document.getElementById("api-url"),
  analyzeBtn: document.getElementById("analyze-btn"),
  status: document.getElementById("status"),
  result: document.getElementById("result"),
  verdict: document.getElementById("verdict"),
  confidence: document.getElementById("confidence"),
  model: document.getElementById("model"),
  textLength: document.getElementById("text-length"),
  explanation: document.getElementById("explanation"),
  sourceUrl: document.getElementById("source-url")
};

function setStatus(message, kind = "info") {
  dom.status.textContent = message;
  dom.status.className = `status status-${kind}`;
}

function hideResult() {
  dom.result.classList.add("hidden");
}

function showResult() {
  dom.result.classList.remove("hidden");
}

function trimApiUrl(value) {
  return value.replace(/\/+$/, "");
}

function toPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }
  return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`;
}

function verdictLabel(isAi) {
  return isAi ? "Likely AI-generated" : "Likely human-written";
}

async function getStoredApiUrl() {
  const stored = await extApi.storage.local.get("apiUrl");
  return stored.apiUrl || DEFAULT_API_URL;
}

async function saveApiUrl(value) {
  await extApi.storage.local.set({ apiUrl: value });
}

async function extractCurrentPageText() {
  const [tab] = await extApi.tabs.query({ active: true, currentWindow: true });
  if (!tab || typeof tab.id !== "number") {
    throw new Error("No active tab found.");
  }

  const blockedProtocols = ["chrome:", "edge:", "about:"];
  if (tab.url && blockedProtocols.some((prefix) => tab.url.startsWith(prefix))) {
    throw new Error("This page cannot be analyzed by the extension.");
  }

  let result;
  if (extApi.scripting && typeof extApi.scripting.executeScript === "function") {
    [{ result }] = await extApi.scripting.executeScript({
      target: { tabId: tab.id },
      func: (maxChars) => {
        const rawText = document.body?.innerText || document.documentElement?.innerText || "";
        const normalized = rawText.replace(/\s+/g, " ").trim();
        return {
          text: normalized.slice(0, maxChars),
          url: window.location.href
        };
      },
      args: [MAX_TEXT_CHARS]
    });
  } else if (extApi.tabs && typeof extApi.tabs.executeScript === "function") {
    const [raw] = await extApi.tabs.executeScript(tab.id, {
      code:
        "(() => {" +
        "const rawText = document.body?.innerText || document.documentElement?.innerText || '';" +
        "const normalized = rawText.replace(/\\s+/g, ' ').trim();" +
        `return { text: normalized.slice(0, ${MAX_TEXT_CHARS}), url: window.location.href };` +
        "})()"
    });
    result = raw;
  } else {
    throw new Error("Browser scripting API is unavailable in this environment.");
  }

  if (!result || typeof result.text !== "string") {
    throw new Error("Could not extract readable text from this page.");
  }

  return result;
}

async function detectText(apiBaseUrl, text) {
  const response = await fetch(`${trimApiUrl(apiBaseUrl)}/api/v1/detect/text`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }

  if (!response.ok) {
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

function renderResult(result, textLength, sourceUrl) {
  dom.verdict.textContent = verdictLabel(Boolean(result.is_ai_generated));
  dom.confidence.textContent = toPercent(result.confidence);
  dom.model.textContent = result.model_prediction || "Unknown";
  dom.textLength.textContent = `${textLength.toLocaleString()} chars`;
  dom.explanation.textContent = result.explanation || "No explanation provided.";
  dom.sourceUrl.textContent = sourceUrl;
  showResult();
}

async function analyzeCurrentPage() {
  hideResult();
  dom.analyzeBtn.disabled = true;
  setStatus("Extracting page text...", "info");

  try {
    const apiUrl = trimApiUrl(dom.apiUrl.value || DEFAULT_API_URL);
    await saveApiUrl(apiUrl);

    const { text, url } = await extractCurrentPageText();
    if (text.length < MIN_TEXT_CHARS) {
      throw new Error("Not enough text on this page to analyze.");
    }

    setStatus("Running AI detection...", "info");
    const result = await detectText(apiUrl, text);
    renderResult(result, text.length, url);
    setStatus("Analysis complete.", "success");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    setStatus(message, "error");
    hideResult();
  } finally {
    dom.analyzeBtn.disabled = false;
  }
}

async function init() {
  const savedApiUrl = await getStoredApiUrl();
  dom.apiUrl.value = savedApiUrl;

  dom.apiUrl.addEventListener("change", async () => {
    const value = trimApiUrl(dom.apiUrl.value || DEFAULT_API_URL);
    dom.apiUrl.value = value;
    await saveApiUrl(value);
  });

  dom.analyzeBtn.addEventListener("click", analyzeCurrentPage);
}

init();
