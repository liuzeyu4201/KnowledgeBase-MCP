const state = {
  requestId: crypto.randomUUID ? crypto.randomUUID() : `web-${Date.now()}`,
  home: {
    page: 1,
    pageSize: 12,
    status: "",
    keyword: "",
  },
  category: {
    page: 1,
    pageSize: 20,
    title: "",
    fileName: "",
    parseStatus: "",
    vectorStatus: "",
  },
  document: {},
  chunkView: {
    page: 1,
    pageSize: 5,
  },
};

async function requestJson(url) {
  const response = await fetch(url, {
    headers: {
      "X-Request-ID": state.requestId,
      "X-Trace-ID": state.requestId,
    },
  });
  const payload = await response.json();
  if (!payload.success) {
    throw new Error(payload.message || "请求失败");
  }
  return payload;
}

async function requestJsonWithMethod(url, method) {
  const response = await fetch(url, {
    method,
    headers: {
      "X-Request-ID": state.requestId,
      "X-Trace-ID": state.requestId,
    },
  });
  const payload = await response.json();
  if (!payload.success) {
    throw new Error(payload.message || "请求失败");
  }
  return payload;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function updatePagination(containerId, pagination, currentPage) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.textContent = `第 ${currentPage} 页 / 共 ${Math.max(1, Math.ceil(pagination.total / pagination.page_size || 1))} 页`;
}

function updateButtonState(prevId, nextId, pagination, currentPage) {
  const prev = document.getElementById(prevId);
  const next = document.getElementById(nextId);
  if (prev) prev.disabled = currentPage <= 1;
  if (next) next.disabled = !pagination.has_next;
}

async function loadHome() {
  const grid = document.getElementById("category-grid");
  const meta = document.getElementById("home-meta");
  const errorBox = document.getElementById("home-error");
  const heroCount = document.getElementById("hero-category-count");
  const summary = document.getElementById("home-pagination-summary");
  errorBox.classList.add("hidden");
  meta.textContent = "正在读取分类数据...";
  grid.innerHTML = "";

  const params = new URLSearchParams({
    page: String(state.home.page),
    page_size: String(state.home.pageSize),
  });
  if (state.home.status) params.set("status", state.home.status);
  if (state.home.keyword) {
    params.set("keyword", state.home.keyword);
  }

  try {
    const payload = await requestJson(`/api/visualization/categories?${params.toString()}`);
    const items = payload.data.items;
    const pagination = payload.data.pagination;
    meta.textContent = `共 ${pagination.total} 个分类，当前展示 ${items.length} 个`;
    heroCount.textContent = pagination.total;
    summary.textContent = `当前页 ${items.length} 项`;
    updatePagination("home-page-indicator", pagination, state.home.page);
    updateButtonState("home-prev-page", "home-next-page", pagination, state.home.page);

    if (!items.length) {
      grid.innerHTML = `<div class="empty-state">当前筛选条件下没有分类。</div>`;
      return;
    }

    grid.innerHTML = items
      .map(
        (item) => `
          <article class="category-card">
            <div class="category-card-top">
              <div class="code-stack">
                <p class="category-code" title="${escapeHtml(item.category_code)}">${escapeHtml(item.category_code)}</p>
                <h3 class="card-title" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</h3>
              </div>
              <span class="badge">${item.document_count} 篇文档</span>
            </div>
            <p class="category-description">${escapeHtml(item.description || "暂无分类描述")}</p>
            <dl class="meta-grid">
              <div><dt>状态</dt><dd>${item.status === 1 ? "启用" : "停用"}</dd></div>
              <div><dt>更新时间</dt><dd>${formatDate(item.updated_at)}</dd></div>
            </dl>
            <a class="card-link" href="/ui/categories/${item.id}">查看该分类文档</a>
          </article>
        `
      )
      .join("");
  } catch (error) {
    meta.textContent = "读取失败";
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
}

function currentCategoryId() {
  const parts = window.location.pathname.split("/");
  return parts[parts.length - 1];
}

function currentDocumentId() {
  const parts = window.location.pathname.split("/");
  const last = parts[parts.length - 1];
  if (last === "chunks") {
    return parts[parts.length - 2];
  }
  return last;
}

async function loadCategoryPage() {
  const title = document.getElementById("category-title");
  const subtitle = document.getElementById("category-subtitle");
  const meta = document.getElementById("document-meta");
  const list = document.getElementById("document-list");
  const errorBox = document.getElementById("category-error");
  const heroDocumentCount = document.getElementById("hero-document-count");
  const summary = document.getElementById("document-pagination-summary");
  errorBox.classList.add("hidden");

  const categoryId = currentCategoryId();
  title.textContent = "分类文档列表";
  subtitle.textContent = "正在读取分类信息...";
  meta.textContent = "正在读取文档数据...";
  list.innerHTML = "";

  const params = new URLSearchParams({
    page: String(state.category.page),
    page_size: String(state.category.pageSize),
  });
  if (state.category.title) params.set("title", state.category.title);
  if (state.category.fileName) params.set("file_name", state.category.fileName);
  if (state.category.parseStatus) params.set("parse_status", state.category.parseStatus);
  if (state.category.vectorStatus) params.set("vector_status", state.category.vectorStatus);

  try {
    const payload = await requestJson(`/api/visualization/categories/${categoryId}/documents?${params.toString()}`);
    const category = payload.data.category;
    const items = payload.data.items;
    const pagination = payload.data.pagination;
    title.textContent = category.name;
    subtitle.textContent = `${category.category_code} · ${category.description || "暂无分类描述"}`;
    meta.textContent = `共 ${pagination.total} 篇文档，当前展示 ${items.length} 篇`;
    heroDocumentCount.textContent = pagination.total;
    summary.textContent = `当前页 ${items.length} 项`;
    updatePagination("document-page-indicator", pagination, state.category.page);
    updateButtonState("document-prev-page", "document-next-page", pagination, state.category.page);

    const deleteCategoryButton = document.getElementById("delete-category-button");
    const deleteCategoryHint = document.getElementById("delete-category-hint");
    if (deleteCategoryButton) {
      deleteCategoryButton.disabled = pagination.total > 0;
    }
    if (deleteCategoryHint) {
      deleteCategoryHint.textContent =
        pagination.total > 0 ? "请先删除该分类下的全部文档，再删除分类" : "当前分类已无文档，可以直接删除分类";
    }

    if (!items.length) {
      list.innerHTML = `<div class="empty-state">当前筛选条件下没有文档。</div>`;
      return;
    }
    list.innerHTML = items
      .map(
        (item) => `
          <article class="document-card">
            <div class="document-card-top">
              <div class="code-stack">
                <h3 class="card-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</h3>
                <p class="document-file" title="${escapeHtml(item.file_name)}">${escapeHtml(item.file_name)}</p>
              </div>
              <span class="badge badge-soft">${escapeHtml(item.mime_type)}</span>
            </div>
            <dl class="meta-grid">
              <div><dt>解析状态</dt><dd>${escapeHtml(item.parse_status)}</dd></div>
              <div><dt>向量状态</dt><dd>${escapeHtml(item.vector_status)}</dd></div>
              <div><dt>切片数</dt><dd>${item.chunk_count}</dd></div>
              <div><dt>版本</dt><dd>${item.version}</dd></div>
              <div><dt>更新时间</dt><dd>${formatDate(item.updated_at)}</dd></div>
              <div><dt>创建时间</dt><dd>${formatDate(item.created_at)}</dd></div>
            </dl>
            <div class="card-actions">
              <a class="card-link" href="/ui/documents/${item.id}">查看原文内容</a>
              <button class="danger-button danger-button-inline" type="button" data-document-delete="${item.id}">删除文档</button>
            </div>
          </article>
        `
      )
      .join("");

    list.querySelectorAll("[data-document-delete]").forEach((button) => {
      button.addEventListener("click", async () => {
        const documentId = button.getAttribute("data-document-delete");
        if (!documentId) return;
        if (!window.confirm(`确认删除文档 #${documentId} 吗？该操作会级联清理 chunk、向量和源文件。`)) {
          return;
        }
        button.disabled = true;
        try {
          await requestJsonWithMethod(`/api/visualization/documents/${documentId}`, "DELETE");
          await loadCategoryPage();
        } catch (error) {
          errorBox.textContent = error.message;
          errorBox.classList.remove("hidden");
        } finally {
          button.disabled = false;
        }
      });
    });
  } catch (error) {
    subtitle.textContent = "读取失败";
    meta.textContent = "读取失败";
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
}

async function loadDocumentPage() {
  const title = document.getElementById("document-title");
  const subtitle = document.getElementById("document-subtitle");
  const meta = document.getElementById("document-meta");
  const metaGrid = document.getElementById("document-meta-grid");
  const errorBox = document.getElementById("document-error");
  const sourceWarning = document.getElementById("document-source-warning");
  const sourcePages = document.getElementById("document-source-pages");
  const heroSourceCount = document.getElementById("hero-source-count");
  const heroSourceStatus = document.getElementById("hero-source-status");
  const heroSourceNote = document.getElementById("hero-source-note");
  const backLink = document.getElementById("document-back-link");
  const chunkLink = document.getElementById("document-chunks-link");
  const deleteButton = document.getElementById("delete-document-button");
  const sourceSummary = document.getElementById("source-pagination-summary");
  const documentId = currentDocumentId();

  errorBox.classList.add("hidden");
  sourceWarning.classList.add("hidden");
  title.textContent = "文档原文详情";
  subtitle.textContent = "正在读取文档信息...";
  meta.textContent = "正在读取文档元数据...";
  metaGrid.innerHTML = "";
  sourcePages.innerHTML = "";

  try {
    const params = new URLSearchParams({
      source_page: String(state.document.sourcePage || 1),
      source_page_size: String(state.document.sourcePageSize || 1),
      chunk_page: "1",
      chunk_page_size: "1",
    });
    const payload = await requestJson(`/api/visualization/documents/${documentId}/content?${params.toString()}`);
    const data = payload.data;
    const documentItem = data.document;

    title.textContent = documentItem.title;
    subtitle.textContent = `${documentItem.file_name} · ${documentItem.mime_type}`;
    meta.textContent = `文档 ID ${documentItem.id} · 版本 ${documentItem.version} · 所属分类 ${documentItem.category?.name || "-"}`;
    heroSourceCount.textContent = data.source_pagination.total;
    heroSourceStatus.textContent = data.source_available ? "可读取" : "不可读取";
    heroSourceNote.textContent = data.source_available ? "原件解析结果已返回" : (data.source_error || "原件不可读，已回退为 chunk 原文");
    if (documentItem.category?.id) {
      backLink.href = `/ui/categories/${documentItem.category.id}`;
    }
    if (chunkLink) {
      chunkLink.href = `/ui/documents/${documentItem.id}/chunks`;
    }
    if (deleteButton) {
      deleteButton.onclick = async () => {
        if (!window.confirm(`确认删除文档《${documentItem.title}》吗？`)) {
          return;
        }
        deleteButton.disabled = true;
        try {
          await requestJsonWithMethod(`/api/visualization/documents/${documentItem.id}`, "DELETE");
          const redirectUrl = documentItem.category?.id ? `/ui/categories/${documentItem.category.id}` : "/ui";
          window.location.href = redirectUrl;
        } catch (error) {
          errorBox.textContent = error.message;
          errorBox.classList.remove("hidden");
          deleteButton.disabled = false;
        }
      };
    }

    sourceSummary.textContent = `当前页 ${data.source_pages.length} 项`;
    updatePagination("source-page-indicator", data.source_pagination, data.source_pagination.page);
    updateButtonState("source-prev-page", "source-next-page", data.source_pagination, data.source_pagination.page);

    metaGrid.innerHTML = `
      <div><dt>分类</dt><dd>${escapeHtml(documentItem.category?.name || "-")}</dd></div>
      <div><dt>分类编码</dt><dd>${escapeHtml(documentItem.category?.category_code || "-")}</dd></div>
      <div><dt>文件名</dt><dd>${escapeHtml(documentItem.file_name)}</dd></div>
      <div><dt>MIME</dt><dd>${escapeHtml(documentItem.mime_type)}</dd></div>
      <div><dt>解析状态</dt><dd>${escapeHtml(documentItem.parse_status)}</dd></div>
      <div><dt>向量状态</dt><dd>${escapeHtml(documentItem.vector_status)}</dd></div>
      <div><dt>切片数</dt><dd>${documentItem.chunk_count}</dd></div>
      <div><dt>文件大小</dt><dd>${documentItem.file_size}</dd></div>
      <div><dt>更新时间</dt><dd>${formatDate(documentItem.updated_at)}</dd></div>
      <div><dt>创建时间</dt><dd>${formatDate(documentItem.created_at)}</dd></div>
    `;

    if (!data.source_available) {
      sourceWarning.textContent = `原件读取失败：${data.source_error || "未知错误"}。页面已回退展示 chunk 原文。`;
      sourceWarning.classList.remove("hidden");
    }

    if (data.source_pages.length) {
      sourcePages.innerHTML = data.source_pages
        .map(
          (page) => `
            <article class="content-card">
              <div class="content-card-top">
                <strong>第 ${page.page_no} 段 / 页</strong>
              </div>
              <pre class="content-text">${escapeHtml(page.content)}</pre>
            </article>
          `
        )
        .join("");
    } else {
      sourcePages.innerHTML = `<div class="empty-state">当前没有可展示的原件解析正文。</div>`;
    }
  } catch (error) {
    subtitle.textContent = "读取失败";
    meta.textContent = "读取失败";
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
}

async function loadChunkPage() {
  const title = document.getElementById("chunk-title");
  const subtitle = document.getElementById("chunk-subtitle");
  const errorBox = document.getElementById("chunk-error");
  const chunks = document.getElementById("document-chunks");
  const chunkSummary = document.getElementById("chunk-pagination-summary");
  const heroChunkCount = document.getElementById("hero-chunk-count");
  const chunkBackLink = document.getElementById("chunk-back-link");
  const chunkDocumentLink = document.getElementById("chunk-document-link");
  const documentId = currentDocumentId();

  errorBox.classList.add("hidden");
  title.textContent = "文档 Chunk 原文";
  subtitle.textContent = "正在读取文档与切片信息...";
  chunks.innerHTML = "";

  try {
    const params = new URLSearchParams({
      chunk_page: String(state.chunkView.page || 1),
      chunk_page_size: String(state.chunkView.pageSize || 5),
    });
    const payload = await requestJson(`/api/visualization/documents/${documentId}/chunks?${params.toString()}`);
    const data = payload.data;
    const documentItem = data.document;

    title.textContent = `${documentItem.title} · Chunk 原文`;
    subtitle.textContent = `${documentItem.file_name} · ${documentItem.mime_type}`;
    heroChunkCount.textContent = data.chunk_pagination.total;
    if (chunkBackLink) {
      chunkBackLink.href = `/ui/documents/${documentItem.id}`;
    }
    if (chunkDocumentLink) {
      chunkDocumentLink.href = `/ui/documents/${documentItem.id}`;
    }

    chunkSummary.textContent = `当前页 ${data.chunks.length} 项`;
    updatePagination("chunk-page-indicator", data.chunk_pagination, data.chunk_pagination.page);
    updateButtonState("chunk-prev-page", "chunk-next-page", data.chunk_pagination, data.chunk_pagination.page);

    if (data.chunks.length) {
      chunks.innerHTML = data.chunks
        .map(
          (chunk) => `
            <article class="content-card">
              <div class="content-card-top">
                <strong>Chunk #${chunk.chunk_no}</strong>
                <span class="badge badge-soft">page ${chunk.page_no ?? "-"}</span>
              </div>
              <dl class="meta-grid meta-grid-compact">
                <div><dt>字符区间</dt><dd>${chunk.char_start ?? "-"} ~ ${chunk.char_end ?? "-"}</dd></div>
                <div><dt>Token 估算</dt><dd>${chunk.token_count ?? "-"}</dd></div>
                <div><dt>向量状态</dt><dd>${escapeHtml(chunk.vector_status)}</dd></div>
                <div><dt>Chunk UID</dt><dd>${escapeHtml(chunk.chunk_uid)}</dd></div>
              </dl>
              <pre class="content-text">${escapeHtml(chunk.content)}</pre>
            </article>
          `
        )
        .join("");
    } else {
      chunks.innerHTML = `<div class="empty-state">当前文档没有已入库的 chunk。</div>`;
    }
  } catch (error) {
    subtitle.textContent = "读取失败";
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  }
}

function connectTaskWebSocket() {
  const taskNotice = document.getElementById("task-notice");
  const taskLog = document.getElementById("task-log");
  if (!taskNotice || !taskLog) {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const taskId = params.get("task_id");
  if (!taskId) {
    taskLog.textContent = "当前未订阅任务。";
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/import-tasks/${taskId}`);
  taskNotice.textContent = `已订阅任务 ${taskId} 的实时状态。`;
  taskNotice.classList.remove("hidden");

  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    taskLog.textContent = JSON.stringify(payload.data || payload.error || payload, null, 2);
  };
  socket.onerror = () => {
    taskNotice.textContent = `任务 ${taskId} 订阅失败。`;
    taskNotice.classList.remove("hidden");
    taskNotice.classList.add("notice-error");
  };
  socket.onclose = () => {
    taskNotice.textContent = `任务 ${taskId} 订阅已结束。`;
    taskNotice.classList.remove("hidden");
  };
}

function bindHomeControls() {
  const apply = document.getElementById("apply-home-filters");
  const refresh = document.getElementById("refresh-home");
  const prev = document.getElementById("home-prev-page");
  const next = document.getElementById("home-next-page");
  const pageSize = document.getElementById("home-page-size");

  if (apply) {
    apply.addEventListener("click", () => {
      state.home.page = 1;
      state.home.keyword = document.getElementById("home-keyword").value.trim();
      state.home.status = document.getElementById("home-status").value;
      state.home.pageSize = Number(pageSize.value);
      void loadHome();
    });
  }
  if (refresh) {
    refresh.addEventListener("click", () => void loadHome());
  }
  if (prev) {
    prev.addEventListener("click", () => {
      if (state.home.page > 1) {
        state.home.page -= 1;
        void loadHome();
      }
    });
  }
  if (next) {
    next.addEventListener("click", () => {
      state.home.page += 1;
      void loadHome();
    });
  }
  if (pageSize) {
    pageSize.addEventListener("change", () => {
      state.home.page = 1;
      state.home.pageSize = Number(pageSize.value);
      void loadHome();
    });
  }
}

function bindCategoryControls() {
  const apply = document.getElementById("apply-category-filters");
  const refresh = document.getElementById("refresh-category");
  const prev = document.getElementById("document-prev-page");
  const next = document.getElementById("document-next-page");
  const pageSize = document.getElementById("document-page-size");

  if (apply) {
    apply.addEventListener("click", () => {
      state.category.page = 1;
      state.category.title = document.getElementById("document-title-filter").value.trim();
      state.category.fileName = document.getElementById("document-file-filter").value.trim();
      state.category.parseStatus = document.getElementById("document-parse-status").value;
      state.category.vectorStatus = document.getElementById("document-vector-status").value;
      state.category.pageSize = Number(pageSize.value);
      void loadCategoryPage();
    });
  }
  if (refresh) {
    refresh.addEventListener("click", () => void loadCategoryPage());
  }
  if (prev) {
    prev.addEventListener("click", () => {
      if (state.category.page > 1) {
        state.category.page -= 1;
        void loadCategoryPage();
      }
    });
  }
  if (next) {
    next.addEventListener("click", () => {
      state.category.page += 1;
      void loadCategoryPage();
    });
  }
  if (pageSize) {
    pageSize.addEventListener("change", () => {
      state.category.page = 1;
      state.category.pageSize = Number(pageSize.value);
      void loadCategoryPage();
    });
  }

  const deleteCategoryButton = document.getElementById("delete-category-button");
  const deleteCategoryHint = document.getElementById("delete-category-hint");
  if (deleteCategoryButton) {
    deleteCategoryButton.addEventListener("click", async () => {
      const categoryId = currentCategoryId();
      if (!window.confirm(`确认删除分类 #${categoryId} 吗？`)) {
        return;
      }
      deleteCategoryButton.disabled = true;
      try {
        await requestJsonWithMethod(`/api/visualization/categories/${categoryId}`, "DELETE");
        window.location.href = "/ui";
      } catch (error) {
        deleteCategoryHint.textContent = error.message;
        deleteCategoryHint.classList.add("danger-text");
        deleteCategoryButton.disabled = false;
      }
    });
  }
}

function bindDocumentControls() {
  const sourcePrev = document.getElementById("source-prev-page");
  const sourceNext = document.getElementById("source-next-page");

  state.document.sourcePage = 1;
  state.document.sourcePageSize = 1;

  if (sourcePrev) {
    sourcePrev.addEventListener("click", () => {
      if ((state.document.sourcePage || 1) > 1) {
        state.document.sourcePage -= 1;
        void loadDocumentPage();
      }
    });
  }
  if (sourceNext) {
    sourceNext.addEventListener("click", () => {
      state.document.sourcePage += 1;
      void loadDocumentPage();
    });
  }
}

function bindChunkControls() {
  const chunkPrev = document.getElementById("chunk-prev-page");
  const chunkNext = document.getElementById("chunk-next-page");

  state.chunkView.page = 1;
  state.chunkView.pageSize = 5;

  if (chunkPrev) {
    chunkPrev.addEventListener("click", () => {
      if ((state.chunkView.page || 1) > 1) {
        state.chunkView.page -= 1;
        void loadChunkPage();
      }
    });
  }
  if (chunkNext) {
    chunkNext.addEventListener("click", () => {
      state.chunkView.page += 1;
      void loadChunkPage();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "home") {
    bindHomeControls();
    void loadHome();
    return;
  }
  if (page === "category") {
    bindCategoryControls();
    void loadCategoryPage();
    connectTaskWebSocket();
    return;
  }
  if (page === "document") {
    bindDocumentControls();
    void loadDocumentPage();
    return;
  }
  if (page === "document-chunks") {
    bindChunkControls();
    void loadChunkPage();
  }
});
