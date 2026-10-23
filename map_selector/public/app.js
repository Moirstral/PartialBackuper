(() => {
  "use strict";

  const REGION = 512;
  const CHUNK = 16;
  const CHUNK_ZOOM = 0.8;
  const MIN_SCALE = 0.005;
  const MAX_SCALE = 8;
  const LS_SELECTIONS = "mc-map-selections-v1";
  const LS_SETTINGS = "mc-map-settings-v1";
  const LS_DRAFT = "mc-map-draft-v1";
  const LS_DISCARDS = "mc-map-discard-v1";
  const ACTIVITY_COLOR = "#f59e0b";

  const DIM_COLORS = {
    "minecraft:overworld": "#4ade9f",
    "minecraft:the_nether": "#fb923c",
    "minecraft:the_end": "#a78bfa",
  };
  const EXTRA_DIM_COLORS = ["#38bdf8", "#f472b6", "#facc15", "#2dd4bf", "#f87171", "#818cf8"];
  const SELECTION_COLORS = ["#4ade9f", "#38bdf8", "#fbbf24", "#f472b6", "#a78bfa", "#facc15", "#2dd4bf", "#fb7185"];
  const FONT_UI = '"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif';
  const FONT_MONO = '"Cascadia Code", Consolas, monospace';
  const PICK_RENDER_LIMIT = 300;

  const $id = (id) => document.getElementById(id);
  const dom = {
    stage: $id("stage"),
    canvas: $id("map"),
    worldIconFallback: $id("worldIconFallback"),
    worldIconImg: $id("worldIconImg"),
    worldName: $id("worldName"),
    worldSub: $id("worldSub"),
    worldPath: $id("worldPath"),
    worldMeta: $id("worldMeta"),
    worldStats: $id("worldStats"),
    statDims: $id("statDims"),
    statRegions: $id("statRegions"),
    statSize: $id("statSize"),
    btnSwitchWorld: $id("btnSwitchWorld"),
    btnRefresh: $id("btnRefresh"),
    dimList: $id("dimList"),
    dimEmpty: $id("dimEmpty"),
    selList: $id("selList"),
    selEmpty: $id("selEmpty"),
    selCount: $id("selCount"),
    regionsSum: $id("regionsSum"),
    exportPreview: $id("exportPreview"),
    exportStats: $id("exportStats"),
    ignoreList: $id("ignoreList"),
    ignoreBlock: $id("ignoreBlock"),
    btnIgnoreBrowse: $id("btnIgnoreBrowse"),
    ignorePick: $id("ignorePick"),
    ignorePickNote: $id("ignorePickNote"),
    ignorePickList: $id("ignorePickList"),
    btnIgnorePickClose: $id("btnIgnorePickClose"),
    ignoreForm: $id("ignoreForm"),
    ignoreInput: $id("ignoreInput"),
    btnPreview: $id("btnPreview"),
    btnCopy: $id("btnCopy"),
    btnDownload: $id("btnDownload"),
    previewDialog: $id("previewDialog"),
    previewSub: $id("previewSub"),
    btnPreviewClose: $id("btnPreviewClose"),
    recoverDialog: $id("recoverDialog"),
    recoverSummary: $id("recoverSummary"),
    recoverError: $id("recoverError"),
    btnRecoverDiscard: $id("btnRecoverDiscard"),
    btnRecoverRestore: $id("btnRecoverRestore"),
    configName: $id("configName"),
    btnConfig: $id("btnConfig"),
    btnBackup: $id("btnBackup"),
    btnBackupText: $id("btnBackupText"),
    selMenu: $id("selMenu"),
    ctxTitle: $id("ctxTitle"),
    ctxActivate: $id("ctxActivate"),
    ctxEdit: $id("ctxEdit"),
    editDialog: $id("editDialog"),
    editForm: $id("editForm"),
    editDesc: $id("editDesc"),
    editCoords: $id("editCoords"),
    editX1: $id("editX1"),
    editZ1: $id("editZ1"),
    editX2: $id("editX2"),
    editZ2: $id("editZ2"),
    editPartsNote: $id("editPartsNote"),
    editError: $id("editError"),
    btnEditSplit: $id("btnEditSplit"),
    btnEditCancel: $id("btnEditCancel"),
    btnEditSave: $id("btnEditSave"),
    configDialog: $id("configDialog"),
    configForm: $id("configForm"),
    configSelect: $id("configSelect"),
    configHint: $id("configHint"),
    configNewName: $id("configNewName"),
    configError: $id("configError"),
    btnConfigCancel: $id("btnConfigCancel"),
    btnConfigLoad: $id("btnConfigLoad"),
    btnConfigSave: $id("btnConfigSave"),
    backupDialog: $id("backupDialog"),
    backupTitle: $id("backupTitle"),
    backupSub: $id("backupSub"),
    backupSummary: $id("backupSummary"),
    backupNoteWrap: $id("backupNoteWrap"),
    backupNote: $id("backupNote"),
    backupOption: $id("backupOption"),
    chunkOnlyToggle: $id("chunkOnlyToggle"),
    chunkOnlyHint: $id("chunkOnlyHint"),
    backupWarning: $id("backupWarning"),
    backupProgress: $id("backupProgress"),
    backupStatus: $id("backupStatus"),
    backupError: $id("backupError"),
    backupLog: $id("backupLog"),
    btnBackupClose: $id("btnBackupClose"),
    btnBackupCopyZip: $id("btnBackupCopyZip"),
    btnBackupStart: $id("btnBackupStart"),
    backupSavePrompt: $id("backupSavePrompt"),
    backupSaveHint: $id("backupSaveHint"),
    btnBackupQuickSave: $id("btnBackupQuickSave"),
    btnActivity: $id("btnActivity"),
    activityDialog: $id("activityDialog"),
    activityMin: $id("activityMin"),
    activitySummary: $id("activitySummary"),
    activityDiscardHint: $id("activityDiscardHint"),
    activityProgress: $id("activityProgress"),
    activityStatus: $id("activityStatus"),
    activityError: $id("activityError"),
    btnActivityClearDiscard: $id("btnActivityClearDiscard"),
    btnActivityCancel: $id("btnActivityCancel"),
    btnActivityStart: $id("btnActivityStart"),
    activityPromptDialog: $id("activityPromptDialog"),
    activityPromptDims: $id("activityPromptDims"),
    btnActivityPromptNo: $id("btnActivityPromptNo"),
    btnActivityPromptYes: $id("btnActivityPromptYes"),
    modeSelect: $id("modeSelect"),
    modePan: $id("modePan"),
    snapToggle: $id("snapToggle"),
    snapLabel: $id("snapLabel"),
    btnNewSelection: $id("btnNewSelection"),
    activeBadge: $id("activeBadge"),
    activeBadgeLead: $id("activeBadgeLead"),
    activeBadgeName: $id("activeBadgeName"),
    activeBadgeHint: $id("activeBadgeHint"),
    btnActiveNew: $id("btnActiveNew"),
    btnActiveDone: $id("btnActiveDone"),
    waypointSwitch: $id("waypointSwitch"),
    waypointToggle: $id("waypointToggle"),
    waypointToggleText: $id("waypointToggleText"),
    btnFit: $id("btnFit"),
    btnZoomOut: $id("btnZoomOut"),
    btnZoomIn: $id("btnZoomIn"),
    zoomLabel: $id("zoomLabel"),
    hudDim: $id("hudDim"),
    hudCoord: $id("hudCoord"),
    hudRegion: $id("hudRegion"),
    renderBadge: $id("renderBadge"),
    renderText: $id("renderText"),
    dragTip: $id("dragTip"),
    activityTip: $id("activityTip"),
    stageEmpty: $id("stageEmpty"),
    btnOpenWorld: $id("btnOpenWorld"),
    btnOpenConfig: $id("btnOpenConfig"),
    worldDialog: $id("worldDialog"),
    worldForm: $id("worldForm"),
    worldPathInput: $id("worldPathInput"),
    dialogError: $id("dialogError"),
    btnDialogCancel: $id("btnDialogCancel"),
    btnDialogOpen: $id("btnDialogOpen"),
    toast: $id("toast"),
    toastText: $id("toastText"),
    toastAction: $id("toastAction"),
  };

  const state = {
    info: null,
    dim: null,
    token: 0,
    hasView: false,
    tiles: new Map(),
    tileQueue: [],
    activeTiles: 0,
    selections: {},
    selStore: {},
    cameras: {},
    camera: { cx: 0, cz: 0, scale: 1 },
    hover: null,
    hoverKey: "",
    drag: null,
    mode: "select",
    snap: true,
    space: false,
    autoFit: true,
    raf: 0,
    toastTimer: null,
    lastPath: "",
    configFile: "",
    configData: null,
    configExtras: [],
    ignores: [],
    ignoreExtras: [],
    saveEntries: null,
    saveEntriesPath: "",
    saveEntriesTruncated: false,
    ignorePickOpen: false,
    pickTree: null,
    pickExpanded: null,
    pickRows: [],
    pickCursor: -1,
    configDirty: false,
    configWorldPath: "",
    configList: [],
    lastConfigFile: "",
    backupJob: null,
    backupTimer: null,
    backupPollErrors: 0,
    backupUnseen: false,
    chunkOnlyBackup: false,
    backupCoverage: null,
    backupItems: null,
    activeSelId: "",
    menuSelId: "",
    editingSelId: "",
    showWaypoints: true,
    waypoints: {},
    waypointAvailable: false,
    waypointTotal: 0,
    waypointToken: 0,
    pendingDraft: null,
    discardStore: {},
    activityBusy: false,
    activityMinDefault: 0,
    activityMinByDim: {},
    activityBackupByDim: {},
    activityPromptTargets: null,
  };
  const LEGACY_FOLDER_DIM = {
    region: "minecraft:overworld",
    "dim-1/region": "minecraft:the_nether",
    dim1: "minecraft:the_end",
    "dim1/region": "minecraft:the_end",
  };

  let ctx = null;
  let saveEntriesPromise = null;
  let dpr = 1;
  let cssW = 1;
  let cssH = 1;

  const icons = {
    focus:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">' +
      '<circle cx="12" cy="12" r="3.2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>',
    trash:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>',
    folder:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h6a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/></svg>',
    file:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5"/></svg>',
    chevron:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M9 5l7 7-7 7"/></svg>',
  };

  // ---------------------------------------------------------------- utils

  function clamp(v, lo, hi) {
    return v < lo ? lo : v > hi ? hi : v;
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function uid() {
    return "sel-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
  }

  function formatBytes(bytes) {
    if (!bytes) return "0 MB";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let value = bytes;
    let i = 0;
    while (value >= 1024 && i < units.length - 1) {
      value /= 1024;
      i += 1;
    }
    const digits = i === 0 || value >= 100 ? 0 : 1;
    return value.toFixed(digits) + " " + units[i];
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.round(seconds));
    if (total < 60) return total + " 秒";
    const minutes = Math.floor(total / 60);
    return minutes + " 分 " + (total % 60) + " 秒";
  }

  function formatStamp(ms, withTime) {
    const date = new Date(Number(ms) || 0);
    if (Number.isNaN(date.getTime())) return "";
    const pad = (n) => String(n).padStart(2, "0");
    const day = date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
    return withTime ? day + " " + pad(date.getHours()) + ":" + pad(date.getMinutes()) : day;
  }

  function formatActivityTicks(ticks) {
    const total = Math.ceil(Math.max(0, Number(ticks) || 0) / 20);
    if (!total) return "0 秒";
    const days = Math.floor(total / 86400);
    const hours = Math.floor((total % 86400) / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    let text = "";
    if (days) text += days + "天";
    if (hours) text += hours + "小时";
    if (minutes) text += minutes + "分";
    if (seconds || !text) text += seconds + "秒";
    return text;
  }

  function activityMinText(seconds) {
    const value = Number(seconds) || 0;
    if (value <= 0) return "0 秒（只要停留过）";
    return value + " 秒 · " + Math.round(value * 20) + " 游戏刻";
  }

  function activityMinFor(dimId) {
    const value = Number(state.activityMinByDim[dimId]);
    if (Number.isFinite(value) && value >= 0) return value;
    return state.activityMinDefault;
  }

  function setActivityMinFor(dimId, seconds) {
    state.activityMinByDim[dimId] = clamp(Math.round(seconds * 1000) / 1000, 0, 365 * 86400);
    saveSettings();
  }

  // Missing entry means on, so the switch defaults to joining the backup.
  function activityBackupOn(dimId) {
    return state.activityBackupByDim[dimId] !== false;
  }

  function setActivityBackup(dimId, on) {
    state.activityBackupByDim[dimId] = !!on;
    saveSettings();
    updateExport();
    requestDraw();
  }

  function hexA(hex, alpha) {
    const n = parseInt(hex.slice(1), 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + alpha + ")";
  }

  function hashString(str) {
    let h = 0;
    for (let i = 0; i < str.length; i += 1) {
      h = (h * 31 + str.charCodeAt(i)) | 0;
    }
    return Math.abs(h);
  }

  function isWorldInfo(data) {
    return !!data && typeof data.path === "string" && Array.isArray(data.dimensions);
  }

  async function api(url, options) {
    const res = await fetch(url, options);
    let data = null;
    const type = res.headers.get("content-type") || "";
    if (type.includes("application/json")) {
      data = await res.json().catch(() => null);
    } else {
      const text = await res.text().catch(() => "");
      data = text ? { error: text } : null;
    }
    if (!res.ok) {
      throw new Error((data && data.error) || "请求失败 (" + res.status + ")");
    }
    return data;
  }

  // ---------------------------------------------------------------- boot

  async function init() {
    ctx = dom.canvas.getContext("2d");
    loadSettings();
    applySettingsToUI();
    bindEvents();
    new ResizeObserver(resizeCanvas).observe(dom.stage);
    window.addEventListener("resize", resizeCanvas);
    resizeCanvas();
    setEmptyState();

    try {
      const data = await api("/api/configs");
      state.configList = Array.isArray(data.configs) ? data.configs : [];
    } catch (err) {
      state.configList = [];
      showToast("无法读取 configs 目录：" + err.message, { error: true, duration: 5000 });
    }

    if (!offerDraftRecovery()) await autoLoadPreferredConfig();

    requestDraw();
    loadBackupStatus();
  }

  async function autoLoadPreferredConfig() {
    const preferred = state.lastConfigFile;
    const item = preferred
      ? state.configList.find((c) => c.file === preferred && !c.error)
      : null;
    if (item) {
      try {
        await loadConfigFile(item.file);
        showToast(
          "已加载上次使用的配置「" + item.file + "」 · " + totalSelectionCount() + " 个选区",
          { duration: 5200 }
        );
      } catch (err) {
        setEmptyState();
        showToast("上次使用的配置加载失败：" + err.message, { error: true, duration: 6000 });
      }
    } else if (preferred) {
      state.lastConfigFile = "";
      saveSettings();
      showToast("上次使用的配置已不存在，请重新选择", { duration: 5000 });
    }
  }

  // ---------------------------------------------------------------- draft

  function hasUnsavedWork() {
    if (!state.info) return false;
    if (state.configFile) return !!state.configDirty;
    return (
      totalSelectionCount() > 0 || state.ignores.length > 0 || state.ignoreExtras.length > 0
    );
  }

  function cacheDraft() {
    if (!hasUnsavedWork()) {
      clearDraft();
      return;
    }
    const draft = {
      version: 1,
      savedAt: Date.now(),
      worldPath: state.info.path,
      worldName: state.info.name || "",
      dim: state.dim || "",
      configFile: state.configFile || "",
      configDirty: !!state.configDirty,
      configData: state.configData,
      configExtras: state.configExtras || [],
      ignores: state.ignores || [],
      ignoreExtras: state.ignoreExtras || [],
      selections: state.selections || {},
    };
    try {
      localStorage.setItem(LS_DRAFT, JSON.stringify(draft));
    } catch (err) {
      /* cache is best-effort */
    }
  }

  function readDraft() {
    let draft = null;
    try {
      const raw = localStorage.getItem(LS_DRAFT);
      if (raw) draft = JSON.parse(raw);
    } catch (err) {
      clearDraft();
      return null;
    }
    if (
      !draft ||
      draft.version !== 1 ||
      typeof draft.worldPath !== "string" ||
      !draft.worldPath
    ) {
      if (draft) clearDraft();
      return null;
    }
    return draft;
  }

  function clearDraft() {
    state.pendingDraft = null;
    try {
      localStorage.removeItem(LS_DRAFT);
    } catch (err) {
      /* ignore */
    }
  }

  function draftSelectionCount(draft) {
    if (!draft.selections || typeof draft.selections !== "object") return 0;
    return Object.values(draft.selections).reduce(
      (sum, list) => sum + (Array.isArray(list) ? list.length : 0),
      0
    );
  }

  function formatDraftTime(value) {
    const date = new Date(Number(value) || 0);
    if (Number.isNaN(date.getTime())) return "未知";
    try {
      return date.toLocaleString("zh-CN", { hour12: false });
    } catch (err) {
      return date.toISOString();
    }
  }

  function addRecoverRow(key, value) {
    dom.recoverSummary.append(
      el("span", "k", key),
      el("span", "v", String(value))
    );
  }

  function offerDraftRecovery() {
    const draft = readDraft();
    if (!draft) return false;
    state.pendingDraft = draft;
    dom.recoverSummary.replaceChildren();
    addRecoverRow("存档", (draft.worldName || "未命名存档") + " · " + draft.worldPath);
    addRecoverRow("配置文件", draft.configFile || "未关联（临时草稿）");
    addRecoverRow("选区", draftSelectionCount(draft) + " 条");
    const ignoreCount =
      (Array.isArray(draft.ignores) ? draft.ignores.length : 0) +
      (Array.isArray(draft.ignoreExtras) ? draft.ignoreExtras.length : 0);
    addRecoverRow("排除项", ignoreCount + " 个");
    addRecoverRow("缓存时间", formatDraftTime(draft.savedAt));
    dom.recoverError.hidden = true;
    dom.btnRecoverRestore.disabled = false;
    dom.btnRecoverDiscard.disabled = false;
    dom.btnRecoverRestore.textContent = "恢复草稿";
    if (!dom.recoverDialog.open) dom.recoverDialog.showModal();
    return true;
  }

  async function restorePendingDraft() {
    const draft = state.pendingDraft;
    if (!draft) return;
    dom.recoverError.hidden = true;
    dom.btnRecoverRestore.disabled = true;
    dom.btnRecoverDiscard.disabled = true;
    dom.btnRecoverRestore.textContent = "恢复中…";
    try {
      const info = await api("/api/world", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: draft.worldPath }),
      });
      if (!isWorldInfo(info)) throw new Error("服务返回的存档数据无效");
      applyWorld(info);

      const selections = selectionMapFrom(draft.selections);
      for (const dimId of Object.keys(selections)) {
        if (!info.dimensions.some((dim) => dim.id === dimId)) delete selections[dimId];
      }
      state.configFile = typeof draft.configFile === "string" ? draft.configFile : "";
      state.configData =
        draft.configData && typeof draft.configData === "object" ? draft.configData : null;
      state.configExtras = Array.isArray(draft.configExtras) ? draft.configExtras : [];
      state.ignoreExtras = Array.isArray(draft.ignoreExtras) ? draft.ignoreExtras : [];
      state.ignores = normalizeIgnores(
        Array.isArray(draft.ignores) ? draft.ignores : []
      );
      state.selections = selections;
      state.configDirty = true;
      state.configWorldPath = info.path;
      if (state.configFile) state.lastConfigFile = state.configFile;
      const preferredDim =
        info.dimensions.find((dim) => dim.id === draft.dim) ||
        info.dimensions.find((dim) => (selections[dim.id] || []).length > 0) ||
        info.dimensions[0] ||
        null;
      state.dim = preferredDim ? preferredDim.id : null;
      state.selStore[info.path] = selections;
      persistSelections();
      renderDims();
      renderSelections();
      updateExport();
      saveSettings();
      if (preferredDim) {
        state.hasView = false;
        state.autoFit = true;
        fitView();
      }
      dom.recoverDialog.close();
      showToast("已恢复未保存的配置草稿", { duration: 5200 });
    } catch (err) {
      dom.recoverError.textContent = err.message || "恢复草稿失败";
      dom.recoverError.hidden = false;
    } finally {
      dom.btnRecoverRestore.disabled = false;
      dom.btnRecoverDiscard.disabled = false;
      dom.btnRecoverRestore.textContent = "恢复草稿";
    }
  }

  async function discardPendingDraft() {
    clearDraft();
    dom.recoverDialog.close();
    await autoLoadPreferredConfig();
    requestDraw();
    loadBackupStatus();
  }

  function bindEvents() {
    dom.btnSwitchWorld.addEventListener("click", openWorldDialog);
    dom.btnOpenWorld.addEventListener("click", openWorldDialog);
    dom.btnOpenConfig.addEventListener("click", () => openConfigDialog(false));
    dom.btnRefresh.addEventListener("click", refreshWorld);
    dom.worldForm.addEventListener("submit", onWorldSubmit);
    dom.btnDialogCancel.addEventListener("click", () => dom.worldDialog.close());
    dom.worldDialog.addEventListener("cancel", (event) => {
      if (dom.btnDialogOpen.disabled) event.preventDefault();
    });
    dom.worldIconImg.addEventListener("error", () => {
      dom.worldIconImg.hidden = true;
      dom.worldIconFallback.hidden = false;
    });

    dom.modeSelect.addEventListener("click", () => setMode("select"));
    dom.modePan.addEventListener("click", () => setMode("pan"));
    dom.snapToggle.addEventListener("change", () => {
      state.snap = dom.snapToggle.checked;
      saveSettings();
      updateHud();
      requestDraw();
    });
    dom.btnNewSelection.addEventListener("click", startNewSelection);
    dom.btnActiveNew.addEventListener("click", startNewSelection);
    dom.btnActiveDone.addEventListener("click", () => {
      if (!state.activeSelId) return;
      state.activeSelId = "";
      updateActiveUI();
      renderSelections();
      requestDraw();
      showToast("已结束当前选区");
    });
    dom.waypointToggle.addEventListener("change", () => {
      state.showWaypoints = dom.waypointToggle.checked;
      saveSettings();
      updateWaypointUI();
      requestDraw();
    });
    dom.btnFit.addEventListener("click", fitView);
    dom.btnZoomIn.addEventListener("click", () => zoomBy(1.3));
    dom.btnZoomOut.addEventListener("click", () => zoomBy(1 / 1.3));

    dom.ignoreForm.addEventListener("submit", (event) => {
      event.preventDefault();
      addIgnore();
    });
    dom.ignoreInput.addEventListener("input", onIgnoreInput);
    dom.ignoreInput.addEventListener("keydown", onIgnoreInputKeydown);
    dom.btnIgnoreBrowse.addEventListener("click", () => {
      if (state.ignorePickOpen) closeIgnorePick();
      else openIgnorePick();
    });
    dom.btnIgnorePickClose.addEventListener("click", closeIgnorePick);
    document.addEventListener(
      "pointerdown",
      (event) => {
        if (!state.ignorePickOpen) return;
        if (dom.ignoreBlock.contains(event.target)) return;
        closeIgnorePick();
      },
      true
    );
    dom.btnPreview.addEventListener("click", openPreviewDialog);
    dom.btnPreviewClose.addEventListener("click", () => dom.previewDialog.close());
    dom.btnCopy.addEventListener("click", copyExport);
    dom.btnDownload.addEventListener("click", downloadExport);
    dom.btnConfig.addEventListener("click", () => openConfigDialog(false));
    dom.editForm.addEventListener("submit", saveEditedSelection);
    dom.btnEditCancel.addEventListener("click", () => dom.editDialog.close());
    dom.btnEditSplit.addEventListener("click", splitSelection);
    dom.selMenu.addEventListener("click", onSelectionMenuClick);
    document.addEventListener(
      "pointerdown",
      (event) => {
        if (dom.selMenu.hidden || dom.selMenu.contains(event.target)) return;
        hideSelectionMenu();
      },
      true
    );
    dom.configForm.addEventListener("submit", saveConfigFromDialog);
    dom.btnConfigCancel.addEventListener("click", () => dom.configDialog.close());
    dom.btnConfigLoad.addEventListener("click", loadConfigFromDialog);
    dom.configSelect.addEventListener("change", updateConfigHint);
    dom.btnRecoverRestore.addEventListener("click", restorePendingDraft);
    dom.btnRecoverDiscard.addEventListener("click", discardPendingDraft);
    dom.recoverDialog.addEventListener("cancel", (event) => event.preventDefault());
    window.addEventListener("beforeunload", (event) => {
      if (!hasUnsavedWork()) return;
      cacheDraft();
      event.preventDefault();
      event.returnValue = "";
    });
    dom.btnBackup.addEventListener("click", openBackupDialog);
    dom.btnBackupStart.addEventListener("click", startBackup);
    dom.btnBackupClose.addEventListener("click", () => dom.backupDialog.close());
    dom.btnBackupCopyZip.addEventListener("click", copyZipPath);
    dom.btnBackupQuickSave.addEventListener("click", quickSaveBackupConfig);
    dom.chunkOnlyToggle.addEventListener("change", onChunkOnlyToggle);
    dom.backupDialog.addEventListener("close", onBackupDialogClose);
    dom.btnActivity.addEventListener("click", openActivityDialog);
    dom.btnActivityStart.addEventListener("click", startActivityScan);
    dom.btnActivityCancel.addEventListener("click", () => dom.activityDialog.close());
    dom.btnActivityClearDiscard.addEventListener("click", clearActivityDiscards);
    dom.activityMin.addEventListener("input", onActivityMinInput);
    dom.activityDialog.addEventListener("cancel", (event) => {
      if (state.activityBusy) event.preventDefault();
    });
    dom.btnActivityPromptNo.addEventListener("click", closeActivityPrompt);
    dom.btnActivityPromptYes.addEventListener("click", runActivityPromptScan);
    dom.activityPromptDialog.addEventListener("cancel", closeActivityPrompt);
    dom.btnRefresh.disabled = true;

    dom.canvas.addEventListener("pointerdown", onPointerDown);
    dom.canvas.addEventListener("pointermove", onPointerMove);
    dom.canvas.addEventListener("pointerup", onPointerUp);
    dom.canvas.addEventListener("pointercancel", onPointerCancel);
    dom.canvas.addEventListener("pointerleave", onPointerLeave);
    dom.canvas.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      if (!currentDim()) {
        hideSelectionMenu();
        return;
      }
      const rect = dom.canvas.getBoundingClientRect();
      const world = screenToWorld(
        clamp(event.clientX - rect.left, 0, cssW),
        clamp(event.clientY - rect.top, 0, cssH)
      );
      if (event.altKey) {
        const sel = hitSelection(world);
        if (sel) openSelectionMenu(sel, event.clientX, event.clientY);
        else hideSelectionMenu();
        return;
      }
      hideSelectionMenu();
      deleteChunkAt(world);
    });
    dom.canvas.addEventListener("mousedown", (event) => {
      if (event.button === 1) event.preventDefault();
    });
    dom.canvas.addEventListener("wheel", onWheel, { passive: false });

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", () => {
      state.space = false;
      cancelDrag();
      hideSelectionMenu();
      updateCanvasCursor();
    });

    dom.toastAction.addEventListener("click", () => {
      const action = dom.toastAction._action;
      hideToast();
      if (typeof action === "function") action();
    });
  }

  // ---------------------------------------------------------------- settings

  function loadSettings() {
    try {
      const saved = JSON.parse(localStorage.getItem(LS_SETTINGS) || "{}");
      if (saved && (saved.mode === "select" || saved.mode === "pan")) state.mode = saved.mode;
      if (saved && typeof saved.snap === "boolean") state.snap = saved.snap;
      if (saved && typeof saved.lastPath === "string") state.lastPath = saved.lastPath;
      if (saved && typeof saved.lastConfigFile === "string") state.lastConfigFile = saved.lastConfigFile;
      if (saved && typeof saved.showWaypoints === "boolean") state.showWaypoints = saved.showWaypoints;
      if (saved && typeof saved.chunkOnlyBackup === "boolean") state.chunkOnlyBackup = saved.chunkOnlyBackup;
      if (saved && Number.isFinite(saved.activityMinSeconds) && saved.activityMinSeconds >= 0) {
        state.activityMinDefault = saved.activityMinSeconds;
      }
      if (saved && saved.activityMinByDim && typeof saved.activityMinByDim === "object") {
        for (const [dimId, value] of Object.entries(saved.activityMinByDim)) {
          if (Number.isFinite(value) && value >= 0) state.activityMinByDim[dimId] = value;
        }
      }
      if (saved && saved.activityBackupByDim && typeof saved.activityBackupByDim === "object") {
        for (const [dimId, value] of Object.entries(saved.activityBackupByDim)) {
          if (typeof value === "boolean") state.activityBackupByDim[dimId] = value;
        }
      }
    } catch (err) {
      /* settings are optional */
    }
  }

  function saveSettings() {
    try {
      localStorage.setItem(
        LS_SETTINGS,
        JSON.stringify({
          mode: state.mode,
          snap: state.snap,
          lastPath: state.lastPath,
          lastConfigFile: state.lastConfigFile,
          showWaypoints: state.showWaypoints,
          chunkOnlyBackup: state.chunkOnlyBackup,
          activityMinSeconds: state.activityMinDefault,
          activityMinByDim: state.activityMinByDim,
          activityBackupByDim: state.activityBackupByDim,
        })
      );
    } catch (err) {
      /* storage may be unavailable */
    }
  }

  function applySettingsToUI() {
    dom.snapToggle.checked = state.snap;
    dom.waypointToggle.checked = state.showWaypoints;
    dom.chunkOnlyToggle.checked = state.chunkOnlyBackup;
    dom.modeSelect.classList.toggle("active", state.mode === "select");
    dom.modePan.classList.toggle("active", state.mode === "pan");
    updateCanvasCursor();
  }

  // ---------------------------------------------------------------- world

  function applyWorld(info, options) {
    const opts = options || {};
    const keepDimId = opts.keepDim ? state.dim : null;
    const keepCamera = opts.keepView ? { ...state.camera } : null;

    if (state.configFile && state.configWorldPath && info.path !== state.configWorldPath) {
      state.configFile = "";
      state.configData = null;
      state.configExtras = [];
      state.ignores = [];
      state.ignoreExtras = [];
      state.configDirty = false;
      state.configWorldPath = "";
    }

    state.token += 1;
    state.info = info;
    state.lastPath = info.path;
    state.drag = null;
    state.hover = null;
    state.hoverKey = "";
    state.activeSelId = "";
    hideSelectionMenu();
    state.cameras = {};
    state.hasView = false;
    dom.dragTip.hidden = true;
    clearTiles();
    resetSaveEntries();
    prepareDimensions(info);
    loadSelections(info.path);
    loadDiscards();
    state.waypoints = {};
    state.waypointAvailable = false;
    state.waypointTotal = 0;
    state.waypointToken += 1;

    const nextDim =
      info.dimensions.find((d) => d.id === keepDimId) ||
      info.dimensions.find((d) => d.id === "minecraft:overworld" && d.regionCount > 0) ||
      info.dimensions.find((d) => d.regionCount > 0) ||
      info.dimensions[0] ||
      null;
    state.dim = nextDim ? nextDim.id : null;

    renderWorld();
    renderDims();
    renderSelections();
    updateExport();
    updateHud();
    updateCanvasCursor();
    setEmptyStageCopy(!!nextDim);
    dom.stageEmpty.hidden = !!nextDim;

    if (nextDim) {
      if (keepCamera) {
        state.camera = keepCamera;
        state.autoFit = false;
        clampCamera();
        state.hasView = true;
        updateHud();
        requestDraw();
      } else {
        state.autoFit = true;
        fitView();
        requestAnimationFrame(() => {
          if (state.autoFit) fitView();
        });
      }
    } else {
      showToast("这个存档中没有找到可显示的 region 目录", { error: true, duration: 4200 });
      requestDraw();
    }
    saveSettings();
    updateRenderBadge();
    loadWaypoints();
  }

  function prepareDimensions(info) {
    for (const dim of info.dimensions) {
      dim._regions = new Map();
      for (const region of dim.regions) {
        region._mask = decodeChunkMask(region.chunks);
        if (!Number.isFinite(region.chunkCount)) {
          region.chunkCount = region._mask ? maskCount(region._mask) : 0;
        }
        dim._regions.set(region.x + "," + region.z, region);
      }
      dim._color = DIM_COLORS[dim.id] || EXTRA_DIM_COLORS[hashString(dim.id) % EXTRA_DIM_COLORS.length];
    }
  }

  function decodeChunkMask(hex) {
    if (typeof hex !== "string" || hex.length !== 256) return null;
    const mask = new Uint8Array(128);
    for (let i = 0; i < 128; i += 1) {
      const value = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
      if (!Number.isFinite(value)) return null;
      mask[i] = value;
    }
    return mask;
  }

  function popcount8(value) {
    let v = value - ((value >> 1) & 0x55);
    v = (v & 0x33) + ((v >> 2) & 0x33);
    return (v + (v >> 4)) & 0x0f;
  }

  function maskCount(mask) {
    let total = 0;
    for (let i = 0; i < mask.length; i += 1) total += popcount8(mask[i]);
    return total;
  }

  function chunkExistsInRegion(region, cx, cz) {
    if (!region) return false;
    const mask = region._mask;
    if (!mask) return true;
    const index = (cz & 31) * 32 + (cx & 31);
    return (mask[index >> 3] & (1 << (index & 7))) !== 0;
  }

  function chunkExists(dim, cx, cz) {
    return chunkExistsInRegion(
      dim._regions.get(Math.floor(cx / 32) + "," + Math.floor(cz / 32)),
      cx,
      cz
    );
  }

  function selectionUnit() {
    return state.camera.scale >= CHUNK_ZOOM ? CHUNK : REGION;
  }

  function unitLabel(unit) {
    return (unit || selectionUnit()) === CHUNK ? "区块" : "区域";
  }

  function setEmptyStageCopy(hasDims) {
    const heading = dom.stageEmpty.querySelector("h2");
    const paragraph = dom.stageEmpty.querySelector("p");
    if (hasDims) {
      heading.textContent = "加载备份配置，开始选区";
      paragraph.textContent = "选择配置后会按其中的 save_path 打开存档，框选区块后即可保存并备份。";
    } else if (state.info) {
      heading.textContent = "没有找到区域文件";
      paragraph.textContent = "这个存档下没有可显示的 region 目录，请确认选择的是包含 level.dat 的存档文件夹。";
    } else {
      heading.textContent = "加载备份配置，开始选区";
      paragraph.textContent = "选择配置后会按其中的 save_path 打开存档。还没有配置时，也可以先直接打开存档框选，再另存为新配置。";
    }
  }

  function setEmptyState() {
    state.info = null;
    state.dim = null;
    state.selections = {};
    state.selStore = {};
    state.hover = null;
    state.hoverKey = "";
    state.drag = null;
    state.hasView = false;
    state.activeSelId = "";
    state.waypoints = {};
    state.waypointAvailable = false;
    state.waypointTotal = 0;
    state.waypointToken += 1;
    hideSelectionMenu();
    clearTiles();
    dom.stageEmpty.hidden = false;
    dom.worldName.textContent = "尚未加载存档";
    dom.worldSub.textContent = "加载配置或直接打开存档";
    dom.worldPath.textContent = "—";
    dom.worldPath.title = "";
    dom.worldMeta.textContent = "";
    dom.worldMeta.hidden = true;
    dom.worldIconImg.hidden = true;
    dom.worldIconFallback.hidden = false;
    dom.worldStats.hidden = true;
    dom.btnRefresh.disabled = true;
    dom.btnIgnoreBrowse.disabled = true;
    closeIgnorePick();
    setEmptyStageCopy(false);
    renderDims();
    renderSelections();
    updateExport();
    updateHud();
    updateRenderBadge();
    requestDraw();
  }

  function renderWorld() {
    const info = state.info;
    if (!info) return;
    dom.worldName.textContent = info.name || "未命名存档";
    const parts = [];
    if (info.version) parts.push(info.version);
    if (info.dataVersion) parts.push("DataVersion " + info.dataVersion);
    dom.worldSub.textContent = parts.length ? parts.join(" · ") : "Minecraft 存档";
    dom.worldPath.textContent = info.path;
    dom.worldPath.title = info.path;
    dom.worldMeta.textContent = info.lastPlayedMs
      ? "最后游玩 " + formatStamp(info.lastPlayedMs, true)
      : "";
    dom.worldMeta.hidden = !info.lastPlayedMs;

    if (info.hasIcon) {
      dom.worldIconImg.src = "/api/icon?v=" + info.iconMtime;
      dom.worldIconImg.hidden = false;
      dom.worldIconFallback.hidden = true;
    } else {
      dom.worldIconImg.hidden = true;
      dom.worldIconFallback.hidden = false;
    }

    const regions = info.dimensions.reduce((sum, d) => sum + d.regionCount, 0);
    const bytes = info.dimensions.reduce((sum, d) => sum + d.bytes, 0);
    dom.statDims.textContent = String(info.dimensions.length);
    dom.statRegions.textContent = String(regions);
    dom.statSize.textContent = formatBytes(bytes);
    dom.worldStats.hidden = false;
    dom.btnRefresh.disabled = false;
    dom.btnIgnoreBrowse.disabled = false;
  }

  async function refreshWorld() {
    if (!state.info) {
      openWorldDialog();
      return;
    }
    if (dom.btnRefresh.disabled) return;
    dom.btnRefresh.disabled = true;
    dom.btnRefresh.textContent = "扫描中…";
    try {
      const info = await api("/api/info?refresh=1");
      if (!isWorldInfo(info)) throw new Error("服务返回的数据无效");
      applyWorld(info, { keepDim: true, keepView: true });
      showToast("已重新扫描区域文件");
    } catch (err) {
      showToast("扫描失败：" + err.message, { error: true, duration: 4200 });
    } finally {
      dom.btnRefresh.disabled = !state.info;
      dom.btnRefresh.textContent = "刷新扫描";
    }
  }

  // ---------------------------------------------------------------- world dialog

  function openWorldDialog() {
    dom.dialogError.hidden = true;
    dom.worldPathInput.value = (state.info && state.info.path) || state.lastPath || "";
    dom.btnDialogCancel.hidden = !state.info;
    if (!dom.worldDialog.open) dom.worldDialog.showModal();
    window.setTimeout(() => {
      dom.worldPathInput.focus();
      dom.worldPathInput.select();
    }, 30);
  }

  async function onWorldSubmit(event) {
    event.preventDefault();
    let path = dom.worldPathInput.value.trim();
    if (path.length > 1 && path.startsWith('"') && path.endsWith('"')) {
      path = path.slice(1, -1).trim();
    }
    if (!path) {
      showDialogError("请输入存档文件夹路径");
      return;
    }
    if (dom.btnDialogOpen.disabled) return;
    dom.dialogError.hidden = true;
    dom.btnDialogOpen.disabled = true;
    dom.btnDialogCancel.disabled = true;
    dom.btnDialogOpen.textContent = "正在读取…";
    try {
      const info = await api("/api/world", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!isWorldInfo(info)) throw new Error("服务返回的数据无效");
      state.lastPath = info.path;
      applyWorld(info);
      dom.worldDialog.close();
      showToast("已加载「" + (info.name || "存档") + "」");
      maybePromptActivityScan(info);
    } catch (err) {
      showDialogError(err.message || "加载失败");
    } finally {
      dom.btnDialogOpen.disabled = false;
      dom.btnDialogCancel.disabled = false;
      dom.btnDialogOpen.textContent = "打开地图";
      dom.btnRefresh.disabled = !state.info;
    }
  }

  function showDialogError(message) {
    dom.dialogError.textContent = message;
    dom.dialogError.hidden = false;
  }

  // ---------------------------------------------------------------- dimensions

  function currentDim() {
    if (!state.info || !state.dim) return null;
    return state.info.dimensions.find((d) => d.id === state.dim) || null;
  }

  function currentSelections() {
    const dim = currentDim();
    if (!dim) return [];
    return state.selections[dim.id] || [];
  }

  function renderDims() {
    dom.dimList.replaceChildren();
    const dims = state.info ? state.info.dimensions : [];
    dom.dimEmpty.hidden = dims.length > 0;
    dom.dimEmpty.textContent = state.info ? "这个存档没有可显示的区域" : "加载存档后显示维度";

    for (const dim of dims) {
      const btn = el("button", "dim-tab" + (dim.id === state.dim ? " active" : ""));
      btn.type = "button";
      btn.style.setProperty("--dim", dim._color || "#4ade9f");
      btn.title = dim.folder;

      const dot = el("span", "dim-dot");
      const text = el("span", "dim-text");
      text.append(
        el("span", "dim-label", dim.label),
        el("span", "dim-sub", dim.regionCount + " 个区域 · " + formatBytes(dim.bytes))
      );
      const badge = el("span", "dim-badge", String(dim.regionCount));
      btn.append(dot, text, badge);
      btn.addEventListener("click", () => selectDim(dim.id));
      dom.dimList.append(btn);
    }
    updateWaypointUI();
  }

  async function loadWaypoints() {
    const token = ++state.waypointToken;
    if (!state.info) return;
    try {
      const data = await api("/api/waypoints");
      if (token !== state.waypointToken) return;
      const dimensions = data && typeof data.dimensions === "object" && data.dimensions ? data.dimensions : {};
      state.waypoints = {};
      for (const [dimId, list] of Object.entries(dimensions)) {
        if (Array.isArray(list)) state.waypoints[dimId] = list;
      }
      state.waypointTotal = Number(data && data.total) || 0;
      state.waypointAvailable = !!(data && data.available && state.waypointTotal);
    } catch (err) {
      if (token !== state.waypointToken) return;
      state.waypoints = {};
      state.waypointAvailable = false;
      state.waypointTotal = 0;
    }
    updateWaypointUI();
    requestDraw();
  }

  function updateWaypointUI() {
    const dim = currentDim();
    const current = dim ? (state.waypoints[dim.id] || []).length : 0;
    const available = state.waypointAvailable && state.waypointTotal > 0;
    dom.waypointSwitch.hidden = !available;
    if (!available) return;
    dom.waypointToggle.checked = state.showWaypoints;
    dom.waypointToggleText.textContent = current ? "路径点 " + current : "路径点";
    dom.waypointSwitch.title =
      "Xaero 路径点 · 当前维度 " + current + " 个 · 全存档 " + state.waypointTotal + " 个";
  }

  function selectDim(dimId) {
    if (!state.info || dimId === state.dim) return;
    const dim = state.info.dimensions.find((d) => d.id === dimId);
    if (!dim) return;
    if (state.dim) state.cameras[state.dim] = { ...state.camera };
    state.dim = dimId;
    state.hover = null;
    state.hoverKey = "";
    state.activeSelId = "";
    hideSelectionMenu();
    const saved = state.cameras[dimId];
    if (saved) {
      state.camera = { ...saved };
      state.hasView = true;
      state.autoFit = false;
      clampCamera();
      updateHud();
      requestDraw();
    } else {
      state.autoFit = true;
      fitView();
    }
    renderDims();
    renderSelections();
    updateExport();
    updateRenderBadge();
    updateCanvasCursor();
  }

  function contentBounds(dim) {
    if (dim.bounds) {
      return { x1: dim.bounds.x1, z1: dim.bounds.z1, x2: dim.bounds.x2, z2: dim.bounds.z2 };
    }
    const sels = state.selections[dim.id] || [];
    if (sels.length) {
      let x1 = Infinity;
      let z1 = Infinity;
      let x2 = -Infinity;
      let z2 = -Infinity;
      for (const sel of sels) {
        x1 = Math.min(x1, Math.floor(sel.x1 / REGION));
        z1 = Math.min(z1, Math.floor(sel.z1 / REGION));
        x2 = Math.max(x2, Math.floor(sel.x2 / REGION));
        z2 = Math.max(z2, Math.floor(sel.z2 / REGION));
      }
      return { x1, z1, x2, z2 };
    }
    return { x1: 0, z1: 0, x2: 0, z2: 0 };
  }

  function fitPadding() {
    return clamp(Math.min(cssW, cssH) * 0.08, 46, 100);
  }

  function fitScaleFor(dim) {
    if (!dim || cssW < 40 || cssH < 40) return MIN_SCALE;
    const b = contentBounds(dim);
    const pad = fitPadding();
    const widthBlocks = (b.x2 - b.x1 + 1) * REGION;
    const heightBlocks = (b.z2 - b.z1 + 1) * REGION;
    return clamp(
      Math.min((cssW - pad * 2) / widthBlocks, (cssH - pad * 2) / heightBlocks),
      MIN_SCALE,
      MAX_SCALE
    );
  }

  function minZoomScale() {
    const dim = currentDim();
    return dim ? fitScaleFor(dim) : MIN_SCALE;
  }

  function fitView() {
    const dim = currentDim();
    if (!dim) return;
    state.autoFit = true;
    if (cssW < 40 || cssH < 40) {
      requestDraw();
      return;
    }
    const b = contentBounds(dim);
    const widthBlocks = (b.x2 - b.x1 + 1) * REGION;
    const heightBlocks = (b.z2 - b.z1 + 1) * REGION;
    state.camera.scale = fitScaleFor(dim);
    state.camera.cx = b.x1 * REGION + widthBlocks / 2;
    state.camera.cz = b.z1 * REGION + heightBlocks / 2;
    state.hasView = true;
    clampCamera();
    updateHud();
    updateRenderBadge();
    requestDraw();
  }

  function clampCamera() {
    const dim = currentDim();
    if (!dim) return;
    const b = contentBounds(dim);
    const worldX1 = b.x1 * REGION;
    const worldX2 = (b.x2 + 1) * REGION;
    const worldZ1 = b.z1 * REGION;
    const worldZ2 = (b.z2 + 1) * REGION;
    const minScale = minZoomScale();
    state.camera.scale = clamp(state.camera.scale, minScale, MAX_SCALE);
    if (state.camera.scale <= minScale + 1e-9) {
      state.camera.cx = (worldX1 + worldX2) / 2;
      state.camera.cz = (worldZ1 + worldZ2) / 2;
      return;
    }
    const marginX = Math.max(1024, (worldX2 - worldX1) * 0.4);
    const marginZ = Math.max(1024, (worldZ2 - worldZ1) * 0.4);
    state.camera.cx = clamp(state.camera.cx, worldX1 - marginX, worldX2 + marginX);
    state.camera.cz = clamp(state.camera.cz, worldZ1 - marginZ, worldZ2 + marginZ);
  }

  // ---------------------------------------------------------------- selections

  function normalizeRect(raw) {
    if (!raw || ![raw.x1, raw.z1, raw.x2, raw.z2].every(Number.isFinite)) return null;
    let x1 = Math.trunc(raw.x1);
    let z1 = Math.trunc(raw.z1);
    let x2 = Math.trunc(raw.x2);
    let z2 = Math.trunc(raw.z2);
    if (x1 > x2) [x1, x2] = [x2, x1];
    if (z1 > z2) [z1, z2] = [z2, z1];
    return { x1, z1, x2, z2 };
  }

  function rectContains(outer, inner) {
    return (
      outer.x1 <= inner.x1 &&
      outer.z1 <= inner.z1 &&
      outer.x2 >= inner.x2 &&
      outer.z2 >= inner.z2
    );
  }

  function mergeRectList(rects) {
    let kept = [];
    for (const raw of rects) {
      const rect = normalizeRect(raw);
      if (!rect) continue;
      const key = partKey(rect);
      if (kept.some((item) => partKey(item) === key)) continue;
      if (kept.some((item) => rectContains(item, rect))) continue;
      for (let i = kept.length - 1; i >= 0; i -= 1) {
        if (rectContains(rect, kept[i])) kept.splice(i, 1);
      }
      kept.push(rect);
    }

    // Stitch adjacent or overlapping rows/columns together so repeated drags
    // along a chunk edge don't leave a long list of one-chunk rectangles.
    let changed = true;
    let guard = 0;
    while (changed && guard < 64) {
      changed = false;
      guard += 1;
      outer: for (let i = 0; i < kept.length; i += 1) {
        const a = kept[i];
        for (let j = i + 1; j < kept.length; j += 1) {
          const b = kept[j];
          if (a.x1 === b.x1 && a.x2 === b.x2 && a.z1 <= b.z2 + 1 && b.z1 <= a.z2 + 1) {
            a.z1 = Math.min(a.z1, b.z1);
            a.z2 = Math.max(a.z2, b.z2);
            kept.splice(j, 1);
            changed = true;
            break outer;
          }
          if (a.z1 === b.z1 && a.z2 === b.z2 && a.x1 <= b.x2 + 1 && b.x1 <= a.x2 + 1) {
            a.x1 = Math.min(a.x1, b.x1);
            a.x2 = Math.max(a.x2, b.x2);
            kept.splice(j, 1);
            changed = true;
            break outer;
          }
        }
      }
      if (changed) {
        const compact = [];
        for (const rect of kept) {
          if (compact.some((other) => rectContains(other, rect))) continue;
          for (let i = compact.length - 1; i >= 0; i -= 1) {
            if (rectContains(rect, compact[i])) compact.splice(i, 1);
          }
          compact.push(rect);
        }
        kept = compact;
      }
    }
    return kept;
  }

  function getParts(sel) {
    if (sel && Array.isArray(sel.parts) && sel.parts.length) return sel.parts;
    return sel ? [{ x1: sel.x1, z1: sel.z1, x2: sel.x2, z2: sel.z2 }] : [];
  }

  function boundsOfParts(parts) {
    let x1 = Infinity;
    let z1 = Infinity;
    let x2 = -Infinity;
    let z2 = -Infinity;
    for (const part of parts) {
      x1 = Math.min(x1, part.x1);
      z1 = Math.min(z1, part.z1);
      x2 = Math.max(x2, part.x2);
      z2 = Math.max(z2, part.z2);
    }
    return { x1, z1, x2, z2 };
  }

  function partKey(part) {
    return part.x1 + "," + part.z1 + "," + part.x2 + "," + part.z2;
  }

  function selectionSignature(sel) {
    return getParts(sel).map(partKey).sort().join("|");
  }

  function normalizeActivity(raw) {
    if (!raw || !Array.isArray(raw.chunks)) return null;
    const chunks = [];
    const seen = new Set();
    for (const item of raw.chunks) {
      if (!Array.isArray(item) || item.length < 3) continue;
      const cx = Math.trunc(Number(item[0]));
      const cz = Math.trunc(Number(item[1]));
      const ticks = Math.round(Number(item[2]));
      if (!Number.isFinite(cx) || !Number.isFinite(cz) || !Number.isFinite(ticks) || ticks <= 0) {
        continue;
      }
      const key = cx + "," + cz;
      if (seen.has(key)) continue;
      seen.add(key);
      chunks.push([cx, cz, ticks]);
    }
    return chunks.length ? { chunks } : null;
  }

  function activityChunkCount(sel) {
    const chunks = sel && sel.activity && sel.activity.chunks;
    return Array.isArray(chunks) ? chunks.length : 0;
  }

  function normalizeSelection(raw) {
    if (!raw) return null;
    const special = raw.special === "activity" ? "activity" : "";
    const rawParts = Array.isArray(raw.parts) ? raw.parts : [];
    // Special activity selections can hold thousands of exact chunk
    // rectangles; the O(n^2) stitcher would freeze the page.
    let parts;
    if (special || rawParts.length > 300) {
      parts = [];
      const seen = new Set();
      for (const item of rawParts) {
        const rect = normalizeRect(item);
        if (!rect) continue;
        const key = partKey(rect);
        if (seen.has(key)) continue;
        seen.add(key);
        parts.push(rect);
      }
    } else {
      parts = mergeRectList(rawParts);
    }
    if (!parts.length) {
      const rect = normalizeRect(raw);
      if (!rect) return null;
      parts = [rect];
    }
    const bounds = boundsOfParts(parts);
    const desc = typeof raw.desc === "string" && raw.desc.trim() ? raw.desc.trim().slice(0, 60) : "选区";
    const id = typeof raw.id === "string" && raw.id ? raw.id : uid();
    const sel = { id, desc, ...bounds };
    if (parts.length > 1) sel.parts = parts;
    if (special) {
      sel.special = special;
      const activity = normalizeActivity(raw.activity);
      if (activity) sel.activity = activity;
    }
    return sel;
  }

  function selectionRegionKeys(sel) {
    const keys = new Set();
    for (const part of getParts(sel)) {
      const rx0 = Math.floor(part.x1 / REGION);
      const rx1 = Math.floor(part.x2 / REGION);
      const rz0 = Math.floor(part.z1 / REGION);
      const rz1 = Math.floor(part.z2 / REGION);
      for (let rx = rx0; rx <= rx1; rx += 1) {
        for (let rz = rz0; rz <= rz1; rz += 1) {
          keys.add(rx + "," + rz);
        }
      }
    }
    return keys;
  }

  function selectionContains(sel, world) {
    for (const part of getParts(sel)) {
      if (
        world.x >= part.x1 &&
        world.x < part.x2 + 1 &&
        world.z >= part.z1 &&
        world.z < part.z2 + 1
      ) {
        return true;
      }
    }
    return false;
  }

  function hitSelection(world) {
    const sels = currentSelections();
    for (let i = sels.length - 1; i >= 0; i -= 1) {
      if (selectionContains(sels[i], world)) return sels[i];
    }
    return null;
  }

  function hitSelectionForDelete(world) {
    const active = findActiveSelection();
    if (active && selectionContains(active, world)) return active;
    return hitSelection(world);
  }

  const activityTimeCache = new WeakMap();

  function activityChunkTime(sel, cx, cz) {
    if (!sel || !sel.activity) return null;
    let map = activityTimeCache.get(sel);
    if (!map) {
      map = new Map();
      for (const item of sel.activity.chunks) map.set(item[0] + "," + item[1], item[2]);
      activityTimeCache.set(sel, map);
    }
    const value = map.get(cx + "," + cz);
    return Number.isFinite(value) ? value : null;
  }

  function findActivitySelectionAt(world) {
    const sels = currentSelections();
    for (let i = sels.length - 1; i >= 0; i -= 1) {
      if (sels[i].special === "activity" && selectionContains(sels[i], world)) return sels[i];
    }
    return null;
  }

  function selectionMapFrom(raw) {
    const result = {};
    if (!raw || typeof raw !== "object") return result;
    for (const [dimId, list] of Object.entries(raw)) {
      if (!Array.isArray(list)) continue;
      const parsed = list.map(normalizeSelection).filter(Boolean);
      if (parsed.length) result[dimId] = parsed;
    }
    return result;
  }

  function loadSelections(worldPath) {
    state.selStore = {};
    try {
      const raw = JSON.parse(localStorage.getItem(LS_SELECTIONS) || "{}");
      if (raw && typeof raw === "object") state.selStore = raw;
    } catch (err) {
      state.selStore = {};
    }
    state.selections = selectionMapFrom(state.selStore[worldPath]);
    state.selStore[worldPath] = state.selections;
  }

  function persistSelections(options) {
    const opts = options || {};
    if (!state.info) return;
    if (!opts.quiet && state.configFile) {
      state.configDirty = true;
      updateConfigUI();
    }
    state.selStore[state.info.path] = state.selections;
    try {
      localStorage.setItem(LS_SELECTIONS, JSON.stringify(state.selStore));
    } catch (err) {
      showToast("无法把选区保存到浏览器本地存储", { error: true, duration: 4200 });
    }
    if (!opts.quiet || !state.configFile) cacheDraft();
  }

  function totalSelectionCount() {
    if (!state.info) return 0;
    return state.info.dimensions.reduce(
      (sum, dim) => sum + ((state.selections[dim.id] || []).length),
      0
    );
  }

  function regionCount(sel) {
    return selectionRegionKeys(sel).size;
  }

  function regionSummary(sel) {
    const keys = Array.from(selectionRegionKeys(sel));
    const names = keys.slice(0, 4).map((key) => "r." + key.replace(",", "."));
    const total = keys.length;
    return names.join(" · ") + (total > names.length ? " … +" + (total - names.length) : "");
  }

  function buildRectsBitmap(rects) {
    const bitmapByRegion = new Map();
    for (const raw of rects) {
      const rect = normalizeRect(raw);
      if (!rect) continue;
      const cx0 = Math.floor(rect.x1 / CHUNK);
      const cx1 = Math.floor(rect.x2 / CHUNK);
      const cz0 = Math.floor(rect.z1 / CHUNK);
      const cz1 = Math.floor(rect.z2 / CHUNK);
      const rx0 = Math.floor(cx0 / 32);
      const rx1 = Math.floor(cx1 / 32);
      const rz0 = Math.floor(cz0 / 32);
      const rz1 = Math.floor(cz1 / 32);
      for (let rx = rx0; rx <= rx1; rx += 1) {
        for (let rz = rz0; rz <= rz1; rz += 1) {
          const key = rx + "," + rz;
          let entry = bitmapByRegion.get(key);
          if (!entry) {
            entry = { rx, rz, bits: new Uint8Array(128) };
            bitmapByRegion.set(key, entry);
          }
          const lx0 = Math.max(cx0, rx * 32) - rx * 32;
          const lx1 = Math.min(cx1, rx * 32 + 31) - rx * 32;
          const lz0 = Math.max(cz0, rz * 32) - rz * 32;
          const lz1 = Math.min(cz1, rz * 32 + 31) - rz * 32;
          for (let lz = lz0; lz <= lz1; lz += 1) {
            const row = lz * 32;
            for (let lx = lx0; lx <= lx1; lx += 1) {
              const index = row + lx;
              entry.bits[index >> 3] |= 1 << (index & 7);
            }
          }
        }
      }
    }
    return bitmapByRegion;
  }

  function bitmapCoveredBy(candidate, covering) {
    for (const [key, entry] of candidate) {
      const other = covering.get(key);
      for (let i = 0; i < 128; i += 1) {
        const bits = entry.bits[i];
        if (!bits) continue;
        if (!other || (bits & ~other.bits[i]) !== 0) return false;
      }
    }
    return true;
  }

  function findCoveringSelection(rects, excludeId) {
    const candidate = buildRectsBitmap(rects);
    if (!candidate.size) return null;
    const maps = [];
    for (const sel of currentSelections()) {
      if (excludeId && sel.id === excludeId) continue;
      if (sel.special === "activity") continue;
      const map = buildRectsBitmap(getParts(sel));
      if (bitmapCoveredBy(candidate, map)) return { sel };
      maps.push(map);
    }
    if (maps.length > 1) {
      const union = new Map();
      for (const map of maps) {
        for (const [key, entry] of map) {
          let target = union.get(key);
          if (!target) {
            target = { rx: entry.rx, rz: entry.rz, bits: new Uint8Array(128) };
            union.set(key, target);
          }
          for (let i = 0; i < 128; i += 1) target.bits[i] |= entry.bits[i];
        }
      }
      if (bitmapCoveredBy(candidate, union)) return { sel: null };
    }
    return null;
  }

  function rectsChunkStats(dim, rects) {
    const bitmapByRegion = buildRectsBitmap(rects);

    let chunks = 0;
    let existing = 0;
    let bytes = 0;
    let fullBytes = 0;
    for (const entry of bitmapByRegion.values()) {
      const region = dim._regions.get(entry.rx + "," + entry.rz);
      const mask = region ? region._mask : null;
      let selected = 0;
      let generated = 0;
      for (let i = 0; i < 128; i += 1) {
        const bits = entry.bits[i];
        if (!bits) continue;
        selected += popcount8(bits);
        if (!region) continue;
        generated += popcount8(mask ? bits & mask[i] : bits);
      }
      chunks += selected;
      existing += generated;
      if (region) {
        if (Number.isFinite(region.size)) fullBytes += region.size;
        if (region.chunkCount > 0 && generated) {
          bytes += region.size * (generated / region.chunkCount);
        }
      }
    }
    return {
      chunks,
      regions: bitmapByRegion.size,
      existing,
      bytes: Math.round(bytes),
      fullBytes: Math.round(fullBytes),
    };
  }

  function selectionCoverage(dim, sels) {
    const rects = [];
    for (const sel of sels) rects.push(...getParts(sel));
    return rectsChunkStats(dim, rects);
  }

  function selectionChunkStats(sel) {
    const dim = currentDim();
    if (!dim || !sel) return { chunks: 0, regions: 0, existing: 0, bytes: 0, fullBytes: 0 };
    return rectsChunkStats(dim, getParts(sel));
  }

  function nextSelectionNumber(sels) {
    let max = 0;
    for (const sel of sels) {
      const match = /^选区\s*(\d+)$/.exec(sel.desc || "");
      if (match) max = Math.max(max, Number(match[1]));
    }
    return max + 1 || sels.length + 1;
  }

  function commitSelectionDrag(bounds) {
    const target = findActiveSelection();
    if (target && target.special === "activity") {
      state.activeSelId = "";
      addSelection(bounds);
      return;
    }
    if (target) addPartToSelection(target.id, bounds);
    else addSelection(bounds);
  }

  function findSelectionById(id) {
    return currentSelections().find((sel) => sel.id === id) || null;
  }

  function findActiveSelection() {
    if (!state.activeSelId) return null;
    const sel = findSelectionById(state.activeSelId);
    if (!sel) state.activeSelId = "";
    return sel;
  }

  function updateActiveUI() {
    const sel = findActiveSelection();
    dom.activeBadge.hidden = !sel;
    if (sel) {
      const special = sel.special === "activity";
      dom.activeBadgeLead.textContent = special ? "活动选区" : "正在添加到";
      dom.activeBadgeName.textContent = sel.desc || "选区";
      dom.activeBadgeHint.textContent = special
        ? "右键区块标记可抛弃 · 拖拽会新建普通选区"
        : "继续拖拽追加";
    }
  }

  function setActiveSelection(id, notify) {
    const sel = id ? findSelectionById(id) : null;
    state.activeSelId = sel ? sel.id : "";
    updateActiveUI();
    renderSelections();
    requestDraw();
    if (notify && sel) {
      showToast(
        sel.special === "activity"
          ? "活动选区「" + sel.desc + "」· 放大后右键区块可标记为可抛弃 · 拖拽会新建普通选区"
          : "正在添加到「" + sel.desc + "」· 继续拖拽即可追加区块",
        { duration: 5600 }
      );
    }
  }

  function startNewSelection() {
    if (!currentDim()) return;
    const had = !!findActiveSelection();
    state.activeSelId = "";
    updateActiveUI();
    renderSelections();
    requestDraw();
    showToast(
      had ? "已结束当前选区 · 下一次拖拽会新建选区" : "在地图上拖拽即可新建选区",
      { duration: 4200 }
    );
  }

  function addSelection(bounds) {
    const dim = currentDim();
    if (!dim) return;
    if (!state.selections[dim.id]) state.selections[dim.id] = [];
    const list = state.selections[dim.id];
    const covering = findCoveringSelection([bounds], "");
    if (covering) {
      if (covering.sel) {
        setActiveSelection(covering.sel.id, false);
        showToast(
          "该范围已被「" + covering.sel.desc + "」完全覆盖，已设为当前选区",
          { duration: 5600 }
        );
      } else {
        showToast("该范围已被现有选区完全覆盖，无需新建", { duration: 5200 });
      }
      return;
    }
    const sel = normalizeSelection({
      id: uid(),
      desc: "选区 " + nextSelectionNumber(list),
      ...bounds,
    });
    if (!sel) return;
    list.push(sel);
    state.activeSelId = sel.id;
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    const stats = rectsChunkStats(dim, getParts(sel));
    showToast(
      "已新建「" +
        sel.desc +
        "」· " +
        stats.chunks +
        " 个区块" +
        (stats.existing && stats.existing !== stats.chunks
          ? "（" + stats.existing + " 个已生成）"
          : "")
    );
  }

  function addPartToSelection(targetId, bounds) {
    const dim = currentDim();
    if (!dim) return;
    const list = state.selections[dim.id] || [];
    const index = list.findIndex((sel) => sel.id === targetId);
    if (index < 0) return;
    const before = list[index];
    if (before.special === "activity") {
      showToast("「" + before.desc + "」是特殊选区，不能手动追加；请用普通拖拽新建选区", {
        duration: 5600,
      });
      return;
    }
    const nextParts = mergeRectList([...getParts(before), bounds]);
    const updated = normalizeSelection({ id: before.id, desc: before.desc, parts: nextParts });
    if (!updated) return;
    if (selectionSignature(updated) === selectionSignature(before)) {
      showToast("这个范围已在当前选区内，无需重复添加", { error: true });
      return;
    }
    const covering = findCoveringSelection([bounds], before.id);
    if (covering) {
      if (covering.sel) {
        setActiveSelection(covering.sel.id, false);
        showToast(
          "该范围已被「" + covering.sel.desc + "」完全覆盖，未添加",
          { duration: 5600 }
        );
      } else {
        showToast("该范围已被其他选区完全覆盖，未添加", { duration: 5200 });
      }
      return;
    }
    list[index] = updated;
    state.activeSelId = updated.id;
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    const stats = rectsChunkStats(dim, getParts(updated));
    showToast(
      "已添加到「" +
        updated.desc +
        "」· 共 " +
        stats.chunks +
        " 个区块 · " +
        getParts(updated).length +
        " 个选区",
      {
        action: "撤销",
        duration: 7000,
        onAction: () => {
          const current = state.selections[dim.id] || [];
          const at = current.findIndex((sel) => sel.id === before.id);
          if (at >= 0) current[at] = before;
          state.activeSelId = before.id;
          persistSelections();
          renderSelections();
          updateExport();
          requestDraw();
        },
      }
    );
  }

  function openSelectionMenu(sel, clientX, clientY) {
    if (!sel) return;
    state.menuSelId = sel.id;
    const special = sel.special === "activity";
    const parts = getParts(sel);
    dom.ctxTitle.textContent = special
      ? (sel.desc || "选区") + " · 包含 " + activityChunkCount(sel) + " 个区块"
      : (sel.desc || "选区") + (parts.length > 1 ? " · " + parts.length + " 个选区" : "");
    dom.ctxActivate.textContent =
      state.activeSelId === sel.id ? "结束当前选区" : "设为当前选区";
    dom.ctxEdit.hidden = special;
    dom.selMenu.hidden = false;
    const rect = dom.selMenu.getBoundingClientRect();
    const left = Math.max(8, Math.min(clientX, window.innerWidth - rect.width - 8));
    const top = Math.max(8, Math.min(clientY, window.innerHeight - rect.height - 8));
    dom.selMenu.style.left = left + "px";
    dom.selMenu.style.top = top + "px";
  }

  function hideSelectionMenu() {
    if (dom.selMenu.hidden) return;
    dom.selMenu.hidden = true;
    state.menuSelId = "";
  }

  function onSelectionMenuClick(event) {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const sel = findSelectionById(state.menuSelId);
    const action = button.dataset.action;
    hideSelectionMenu();
    if (!sel) return;
    if (action === "edit") openEditDialog(sel);
    else if (action === "focus") focusSelection(sel);
    else if (action === "activate") {
      if (state.activeSelId === sel.id) {
        state.activeSelId = "";
        updateActiveUI();
        renderSelections();
        requestDraw();
        showToast("已结束当前选区");
      } else {
        setActiveSelection(sel.id, true);
      }
    } else if (action === "delete") deleteSelection(sel.id);
  }

  function openEditDialog(sel) {
    if (!sel) return;
    if (sel.special === "activity") {
      showToast("活跃区块不能改名；右键区块可标记为可抛弃，或直接删除整个选区", { duration: 5200 });
      return;
    }
    state.editingSelId = sel.id;
    const parts = getParts(sel);
    const merged = parts.length > 1;
    dom.editDesc.value = sel.desc || "";
    dom.editCoords.hidden = merged;
    dom.editPartsNote.hidden = !merged;
    dom.btnEditSplit.hidden = !merged;
    dom.editError.hidden = true;
    if (merged) {
      dom.editPartsNote.textContent =
        "这个选区包含 " + parts.length + " 个选区，整体范围为 X " + sel.x1 + " → " +
        sel.x2 + "、Z " + sel.z1 + " → " + sel.z2 + "。可修改名称，或拆分为独立选区。";
    } else {
      dom.editX1.value = String(sel.x1);
      dom.editZ1.value = String(sel.z1);
      dom.editX2.value = String(sel.x2);
      dom.editZ2.value = String(sel.z2);
    }
    if (!dom.editDialog.open) dom.editDialog.showModal();
    window.setTimeout(() => {
      dom.editDesc.focus();
      dom.editDesc.select();
    }, 30);
  }

  function saveEditedSelection(event) {
    event.preventDefault();
    const dim = currentDim();
    if (!dim) return;
    const list = state.selections[dim.id] || [];
    const index = list.findIndex((sel) => sel.id === state.editingSelId);
    if (index < 0) {
      dom.editDialog.close();
      return;
    }
    const sel = list[index];
    if (sel.special === "activity") {
      dom.editDialog.close();
      return;
    }
    const desc = dom.editDesc.value.trim().slice(0, 60) || "选区";
    let updated = null;
    if (getParts(sel).length > 1) {
      updated = { ...sel, desc };
    } else {
      const values = [dom.editX1, dom.editZ1, dom.editX2, dom.editZ2].map((input) =>
        input.value.trim()
      );
      if (values.some((value) => value === "")) {
        showEditError("请填写完整的 X1、Z1、X2、Z2");
        return;
      }
      const nums = values.map(Number);
      if (!nums.every(Number.isFinite)) {
        showEditError("坐标必须是数字");
        return;
      }
      updated = normalizeSelection({
        id: sel.id,
        desc,
        x1: nums[0],
        z1: nums[1],
        x2: nums[2],
        z2: nums[3],
      });
      if (!updated) {
        showEditError("坐标无效");
        return;
      }
    }
    if (
      list.some(
        (item) => item.id !== sel.id && selectionSignature(item) === selectionSignature(updated)
      )
    ) {
      showEditError("已有完全相同的选区，无法保存");
      return;
    }
    list[index] = updated;
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    dom.editDialog.close();
    showToast("已更新「" + updated.desc + "」");
  }

  function showEditError(message) {
    dom.editError.textContent = message;
    dom.editError.hidden = false;
  }

  function splitSelection() {
    const dim = currentDim();
    if (!dim) return;
    const list = state.selections[dim.id] || [];
    const index = list.findIndex((sel) => sel.id === state.editingSelId);
    if (index < 0) {
      dom.editDialog.close();
      return;
    }
    const sel = list[index];
    if (sel.special === "activity") {
      dom.editDialog.close();
      showToast("活跃区块特殊选区不能拆分；配置中按维度只保存最小活动时间，加载时会重新扫描", { duration: 5200 });
      return;
    }
    const parts = getParts(sel);
    if (parts.length < 2) return;
    const before = list.slice();
    const name = sel.desc || "选区";
    const pieces = parts
      .map((part, i) =>
        normalizeSelection({
          id: uid(),
          desc: name + " · " + (i + 1),
          ...part,
        })
      )
      .filter(Boolean);
    list.splice(index, 1, ...pieces);
    if (state.activeSelId === sel.id) state.activeSelId = "";
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    dom.editDialog.close();
    showToast("已拆分为 " + pieces.length + " 个选区", {
      action: "撤销",
      duration: 7000,
      onAction: () => {
        state.selections[dim.id] = before;
        persistSelections();
        renderSelections();
        updateExport();
        requestDraw();
      },
    });
  }

  function deleteSelection(id) {
    const dim = currentDim();
    if (!dim) return;
    const list = state.selections[dim.id];
    if (!list) return;
    const index = list.findIndex((sel) => sel.id === id);
    if (index < 0) return;
    const [removed] = list.splice(index, 1);
    if (state.activeSelId === removed.id) state.activeSelId = "";
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    showToast("已删除「" + removed.desc + "」", {
      action: "撤销",
      duration: 6000,
      onAction: () => {
        const current = state.selections[dim.id] || (state.selections[dim.id] = []);
        if (!current.some((sel) => sel.id === removed.id)) {
          current.splice(Math.min(index, current.length), 0, removed);
        }
        persistSelections();
        renderSelections();
        updateExport();
        requestDraw();
      },
    });
  }

  function subtractRectFromParts(parts, cut) {
    const result = [];
    for (const part of parts) {
      if (cut.x2 < part.x1 || cut.x1 > part.x2 || cut.z2 < part.z1 || cut.z1 > part.z2) {
        result.push(part);
        continue;
      }
      const ix1 = Math.max(part.x1, cut.x1);
      const ix2 = Math.min(part.x2, cut.x2);
      const iz1 = Math.max(part.z1, cut.z1);
      const iz2 = Math.min(part.z2, cut.z2);
      if (part.z1 < iz1) {
        result.push({ x1: part.x1, z1: part.z1, x2: part.x2, z2: iz1 - 1 });
      }
      if (iz2 < part.z2) {
        result.push({ x1: part.x1, z1: iz2 + 1, x2: part.x2, z2: part.z2 });
      }
      if (part.x1 < ix1) {
        result.push({ x1: part.x1, z1: iz1, x2: ix1 - 1, z2: iz2 });
      }
      if (ix2 < part.x2) {
        result.push({ x1: ix2 + 1, z1: iz1, x2: part.x2, z2: iz2 });
      }
    }
    return result;
  }

  function deleteChunkAt(world) {
    const dim = currentDim();
    if (!dim) return;
    if (selectionUnit() !== CHUNK) {
      const hit = hitSelectionForDelete(world);
      if (hit) {
        showToast(
          hit.special === "activity"
            ? "放大到 " + Math.round(CHUNK_ZOOM * 100) + "% 以上后，右键可把区块标记为可抛弃"
            : "放大到 " + Math.round(CHUNK_ZOOM * 100) + "% 以上后，右键可删除单个区块",
          { duration: 4600 }
        );
      }
      return;
    }
    const sel = hitSelectionForDelete(world);
    if (!sel) return;
    if (sel.special === "activity") {
      markChunkDiscard(sel, world);
      return;
    }
    const list = state.selections[dim.id] || [];
    const index = list.findIndex((item) => item.id === sel.id);
    if (index < 0) return;
    const cx = Math.floor(world.x / CHUNK);
    const cz = Math.floor(world.z / CHUNK);
    const cut = {
      x1: cx * CHUNK,
      z1: cz * CHUNK,
      x2: cx * CHUNK + CHUNK - 1,
      z2: cz * CHUNK + CHUNK - 1,
    };
    const nextParts = mergeRectList(subtractRectFromParts(getParts(sel), cut));
    const before = list.slice();
    const beforeActive = state.activeSelId;
    let message;
    if (!nextParts.length) {
      list.splice(index, 1);
      if (state.activeSelId === sel.id) {
        state.activeSelId = "";
        updateActiveUI();
      }
      message = "已删除「" + sel.desc + "」的最后一个区块，选区已移除";
    } else {
      const updated = normalizeSelection({ id: sel.id, desc: sel.desc, parts: nextParts });
      if (!updated) return;
      list[index] = updated;
      message =
        "已从「" + sel.desc + "」删除区块 X " + cx * CHUNK + " · Z " + cz * CHUNK;
    }
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    showToast(message, {
      action: "撤销",
      duration: 7000,
      onAction: () => {
        state.selections[dim.id] = before;
        state.activeSelId = beforeActive;
        updateActiveUI();
        persistSelections();
        renderSelections();
        updateExport();
        requestDraw();
      },
    });
  }

  function markChunkDiscard(sel, world) {
    const dim = currentDim();
    if (!dim) return;
    const list = state.selections[dim.id] || [];
    const index = list.findIndex((item) => item.id === sel.id);
    if (index < 0) return;
    const cx = Math.floor(world.x / CHUNK);
    const cz = Math.floor(world.z / CHUNK);
    const key = cx + "," + cz;
    const cut = {
      x1: cx * CHUNK,
      z1: cz * CHUNK,
      x2: cx * CHUNK + CHUNK - 1,
      z2: cz * CHUNK + CHUNK - 1,
    };
    const nextParts = subtractRectFromParts(getParts(sel), cut);
    const before = list.slice();
    const beforeActive = state.activeSelId;
    let activityUpdate = null;
    if (sel.activity) {
      const remaining = sel.activity.chunks.filter(
        (item) => !(item[0] === cx && item[1] === cz)
      );
      if (remaining.length) activityUpdate = { chunks: remaining };
    }
    addDiscardKey(dim.id, key);
    let message;
    if (!nextParts.length) {
      list.splice(index, 1);
      if (state.activeSelId === sel.id) {
        state.activeSelId = "";
        updateActiveUI();
      }
      message = "已把区块 X " + cx * CHUNK + " · Z " + cz * CHUNK + " 标记为可抛弃，活动选区已移除";
    } else {
      const updated = normalizeSelection({
        id: sel.id,
        desc: sel.desc,
        special: "activity",
        parts: nextParts,
        activity: activityUpdate,
      });
      if (!updated) return;
      list[index] = updated;
      message =
        "已把区块 X " + cx * CHUNK + " · Z " + cz * CHUNK + " 标记为可抛弃，并从「" +
        sel.desc + "」移除";
    }
    persistSelections();
    renderSelections();
    updateExport();
    requestDraw();
    showToast(message, {
      action: "撤销",
      duration: 7000,
      onAction: () => {
        removeDiscardKey(dim.id, key);
        state.selections[dim.id] = before;
        state.activeSelId = beforeActive;
        updateActiveUI();
        persistSelections();
        renderSelections();
        updateExport();
        requestDraw();
      },
    });
  }

  function focusSelection(sel) {
    const pad = clamp(Math.min(cssW, cssH) * 0.1, 60, 130);
    const widthBlocks = sel.x2 - sel.x1 + 1;
    const heightBlocks = sel.z2 - sel.z1 + 1;
    const scale = clamp(
      Math.min((cssW - pad * 2) / widthBlocks, (cssH - pad * 2) / heightBlocks),
      minZoomScale(),
      MAX_SCALE
    );
    state.camera.scale = scale;
    state.camera.cx = (sel.x1 + sel.x2 + 1) / 2;
    state.camera.cz = (sel.z1 + sel.z2 + 1) / 2;
    state.autoFit = false;
    clampCamera();
    updateHud();
    requestDraw();
  }

  function activityBackupToggle(dimId) {
    const label = document.createElement("label");
    label.className = "sel-backup-toggle";
    label.title = "开启时活跃区块参与备份；关闭后只在地图上作参考";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = activityBackupOn(dimId);
    box.addEventListener("change", () => {
      setActivityBackup(dimId, box.checked);
      showToast(
        box.checked ? "活跃区块将参与备份" : "活跃区块仅作参考，不参与备份",
        { duration: 4200 }
      );
    });
    label.append(box, el("span", "", "参与备份"));
    label.addEventListener("click", (event) => event.stopPropagation());
    return label;
  }

  function renderSelections() {
    const dim = currentDim();
    const sels = currentSelections();
    dom.selList.replaceChildren();
    dom.selCount.textContent = String(sels.length);
    dom.selEmpty.textContent = dim
      ? "在右侧地图上按住左键拖拽；放大后可按 16×16 区块框选，继续拖拽会追加到当前选区。"
      : "加载存档后可框选区块。";
    dom.selEmpty.hidden = sels.length > 0;

    sels.forEach((sel, index) => {
      const special = sel.special === "activity";
      const color = special ? ACTIVITY_COLOR : SELECTION_COLORS[index % SELECTION_COLORS.length];
      const parts = getParts(sel);
      const active = state.activeSelId === sel.id;
      const card = el(
        "article",
        "sel-card" + (active ? " active" : "") + (special ? " special" : "")
      );
      card.style.setProperty("--c", color);
      card.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        openSelectionMenu(sel, event.clientX, event.clientY);
      });
      card.addEventListener("click", (event) => {
        if (event.target.closest("input, button")) return;
        if (state.activeSelId !== sel.id) setActiveSelection(sel.id, true);
      });
      const bar = el("div", "sel-bar");
      const body = el("div", "sel-body");
      const top = el("div", "sel-top");

      let titleNode;
      if (special) {
        titleNode = el("div", "sel-desc static", sel.desc || "活跃区块");
        titleNode.title = "活跃区块名称固定，不能修改";
      } else {
        const input = document.createElement("input");
        input.className = "sel-desc";
        input.value = sel.desc;
        input.maxLength = 60;
        input.title = "点击修改名称";
        input.addEventListener("input", () => {
          sel.desc = input.value;
          updateActiveUI();
          persistSelections();
          updateExport();
          requestDraw();
        });
        input.addEventListener("blur", () => {
          const text = input.value.trim();
          sel.desc = text || "选区 " + (index + 1);
          input.value = sel.desc;
          updateActiveUI();
          persistSelections();
          updateExport();
          requestDraw();
        });
        input.addEventListener("keydown", (event) => {
          if (event.key === "Enter") input.blur();
        });
        titleNode = input;
      }

      const focusBtn = el("button", "icon-btn");
      focusBtn.type = "button";
      focusBtn.title = "定位到此选区";
      focusBtn.innerHTML = icons.focus;
      focusBtn.addEventListener("click", () => focusSelection(sel));

      const delBtn = el("button", "icon-btn del");
      delBtn.type = "button";
      delBtn.title = "删除选区";
      delBtn.innerHTML = icons.trash;
      delBtn.addEventListener("click", () => deleteSelection(sel.id));

      top.append(titleNode, focusBtn, delBtn);

      const coords = el("div", "sel-coords");
      coords.append(
        el("span", "", "X " + sel.x1 + " → " + sel.x2),
        el("span", "", "Z " + sel.z1 + " → " + sel.z2)
      );

      const foot = el("div", "sel-foot");
      const total = regionCount(sel);
      const stats = selectionChunkStats(sel);
      const summary = regionSummary(sel);
      const regionSpan = el("span", "sel-region-list", summary);
      regionSpan.title = summary;
      const chunkText = special
        ? stats.chunks + " 区块"
        : stats.chunks +
          " 区块" +
          (stats.existing && stats.existing !== stats.chunks
            ? "（" + stats.existing + " 已生成）"
            : "");
      foot.append(el("span", "", chunkText));
      if (active) foot.append(el("span", "sel-active-tag", "当前"));
      if (special) {
        const tag = el("span", "sel-special-tag", "活跃");
        tag.title = "悬停地图上的活跃区块可查看该区块时长";
        card.title = tag.title;
        foot.append(tag, activityBackupToggle(dim.id));
      }
      if (!special && parts.length > 1) {
        foot.append(el("span", "sel-parts", parts.length + " 个选区"));
      }
      foot.append(regionSpan);
      foot.title = "覆盖 " + total + " 个区域文件";

      body.append(top, coords, foot);
      card.append(bar, body);
      dom.selList.append(card);
    });

    updateActiveUI();
    updateSelectionStats();
  }

  function updateSelectionStats() {
    const dim = currentDim();
    const sels = currentSelections();
    if (!dim || !sels.length) {
      dom.regionsSum.textContent = "";
      return;
    }
    const coverage = selectionCoverage(dim, sels);
    dom.regionsSum.textContent =
      coverage.chunks +
      " 区块 · " +
      coverage.regions +
      " 区域 · 约 " +
      formatBytes(coverage.bytes);
  }

  // ---------------------------------------------------------------- activity

  function loadDiscards() {
    const store = {};
    try {
      const raw = JSON.parse(localStorage.getItem(LS_DISCARDS) || "{}");
      if (raw && typeof raw === "object" && !Array.isArray(raw)) {
        for (const [worldPath, dims] of Object.entries(raw)) {
          if (!dims || typeof dims !== "object" || Array.isArray(dims)) continue;
          const clean = {};
          for (const [dimId, list] of Object.entries(dims)) {
            if (!Array.isArray(list)) continue;
            const keys = [];
            const seen = new Set();
            for (const key of list) {
              if (typeof key !== "string" || !/^-?\d+,-?\d+$/.test(key) || seen.has(key)) continue;
              seen.add(key);
              keys.push(key);
            }
            if (keys.length) clean[dimId] = keys;
          }
          if (Object.keys(clean).length) store[worldPath] = clean;
        }
      }
    } catch (err) {
      /* discard marks are optional */
    }
    state.discardStore = store;
  }

  function discardKeys(dimId) {
    if (!state.info || !dimId) return [];
    const dims = state.discardStore[state.info.path];
    const list = dims && dims[dimId];
    return Array.isArray(list) ? list : [];
  }

  function saveDiscards() {
    for (const [worldPath, dims] of Object.entries(state.discardStore)) {
      if (!dims || !Object.keys(dims).length) delete state.discardStore[worldPath];
    }
    try {
      localStorage.setItem(LS_DISCARDS, JSON.stringify(state.discardStore));
    } catch (err) {
      showToast("无法保存可抛弃区块标记", { error: true, duration: 4200 });
    }
  }

  function addDiscardKey(dimId, key) {
    if (!state.info) return;
    const path = state.info.path;
    if (!state.discardStore[path]) state.discardStore[path] = {};
    const dims = state.discardStore[path];
    if (!dims[dimId]) dims[dimId] = [];
    if (!dims[dimId].includes(key)) dims[dimId].push(key);
    saveDiscards();
  }

  function removeDiscardKey(dimId, key) {
    if (!state.info) return;
    const dims = state.discardStore[state.info.path];
    const list = dims && dims[dimId];
    if (!Array.isArray(list)) return;
    const index = list.indexOf(key);
    if (index >= 0) list.splice(index, 1);
    if (!list.length && dims) delete dims[dimId];
    saveDiscards();
  }

  function clearDiscardKeys(dimId) {
    if (!state.info) return 0;
    const dims = state.discardStore[state.info.path];
    const list = dims && dims[dimId];
    const count = Array.isArray(list) ? list.length : 0;
    if (dims) delete dims[dimId];
    saveDiscards();
    return count;
  }

  function addActivityRow(key, value) {
    dom.activitySummary.append(el("span", "k", key), el("span", "v", String(value)));
  }

  function readActivityMinSeconds() {
    const raw = dom.activityMin.value.trim();
    if (raw === "") return 0;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) return null;
    return Math.min(Math.round(value * 1000) / 1000, 365 * 86400);
  }

  function renderActivitySummary(dim, existing, minSeconds) {
    const discs = discardKeys(dim.id).length;
    dom.activitySummary.replaceChildren();
    addActivityRow("维度", dim.label + " · " + dim.folder);
    addActivityRow("扫描范围", dim.regionCount + " 个区域文件 · " + formatBytes(dim.bytes));
    addActivityRow("最小活动时间", activityMinText(minSeconds) + "（本维度）");
    addActivityRow(
      "判定依据",
      minSeconds > 0
        ? "InhabitedTime ≥ " + Math.round(minSeconds * 20) + " 刻（玩家停留时间近似）"
        : "InhabitedTime > 0（玩家停留时间近似）"
    );
    if (existing) {
      const stats = selectionChunkStats(existing);
      addActivityRow(
        "现有活动选区",
        "包含 " + stats.chunks + " 个区块"
      );
    } else {
      addActivityRow("现有活动选区", "无");
    }
    addActivityRow("可抛弃标记", discs + " 个区块");
  }

  function openActivityDialog() {
    const dim = currentDim();
    if (!dim) {
      showToast("请先加载存档并选择维度", { error: true, duration: 3600 });
      return;
    }
    const existing = currentSelections().find((sel) => sel.special === "activity");
    const discs = discardKeys(dim.id).length;
    const minSeconds = activityMinFor(dim.id);
    state.activityBusy = false;
    dom.activityError.hidden = true;
    dom.activityProgress.hidden = true;
    dom.activityStatus.textContent = "正在扫描区域文件…";
    dom.activityMin.value = String(minSeconds);
    dom.activityMin.disabled = false;
    dom.btnActivityStart.disabled = false;
    dom.btnActivityCancel.disabled = false;
    dom.btnActivityClearDiscard.disabled = false;
    dom.btnActivityStart.textContent = existing ? "重新扫描并更新" : "开始扫描";
    dom.btnActivityClearDiscard.hidden = discs === 0;
    dom.btnActivityClearDiscard.textContent = "清除可抛弃标记（" + discs + "）";
    dom.activityDiscardHint.hidden = discs === 0;
    dom.activityDiscardHint.textContent =
      "本维度已有 " + discs + " 个可抛弃区块标记，扫描时会自动排除；标记保存在本机浏览器中，重新扫描不会丢失。";
    renderActivitySummary(dim, existing, minSeconds);
    if (!dom.activityDialog.open) dom.activityDialog.showModal();
  }

  function onActivityMinInput() {
    const dim = currentDim();
    if (!dim || !dom.activityDialog.open) return;
    const parsed = readActivityMinSeconds();
    if (parsed === null) return;
    setActivityMinFor(dim.id, parsed);
    markActivityConfigChangedIfNeeded();
    const existing = currentSelections().find((sel) => sel.special === "activity");
    renderActivitySummary(dim, existing, parsed);
  }

  function activityRectsFromRegions(regions, discardSet) {
    const discardsByRegion = new Map();
    for (const key of discardSet) {
      const comma = key.indexOf(",");
      const cx = Number(key.slice(0, comma));
      const cz = Number(key.slice(comma + 1));
      if (!Number.isInteger(cx) || !Number.isInteger(cz)) continue;
      const regionKey = Math.floor(cx / 32) + "," + Math.floor(cz / 32);
      let list = discardsByRegion.get(regionKey);
      if (!list) {
        list = new Set();
        discardsByRegion.set(regionKey, list);
      }
      list.add((cz & 31) * 32 + (cx & 31));
    }

    const rects = [];
    const times = [];
    let chunks = 0;
    for (const region of regions) {
      const mask = decodeChunkMask(region.mask);
      if (!mask) continue;
      const dropped = discardsByRegion.get(region.x + "," + region.z);
      if (dropped) {
        for (const index of dropped) {
          mask[index >> 3] &= ~(1 << (index & 7));
        }
      }
      for (let i = 0; i < 128; i += 1) chunks += popcount8(mask[i]);

      const baseX = region.x * 32;
      const baseZ = region.z * 32;
      if (Array.isArray(region.times)) {
        for (const item of region.times) {
          if (!Array.isArray(item) || item.length < 2) continue;
          const index = Math.trunc(Number(item[0]));
          const ticks = Math.round(Number(item[1]));
          if (!Number.isInteger(index) || index < 0 || index > 1023) continue;
          if (!Number.isFinite(ticks) || ticks <= 0) continue;
          if ((mask[index >> 3] & (1 << (index & 7))) === 0) continue;
          times.push([baseX + (index % 32), baseZ + Math.floor(index / 32), ticks]);
        }
      }
      let prev = new Map();
      for (let lz = 0; lz < 32; lz += 1) {
        const runs = [];
        let start = -1;
        for (let lx = 0; lx < 32; lx += 1) {
          const index = lz * 32 + lx;
          const on = (mask[index >> 3] & (1 << (index & 7))) !== 0;
          if (on && start < 0) start = lx;
          else if (!on && start >= 0) {
            runs.push([start, lx - 1]);
            start = -1;
          }
        }
        if (start >= 0) runs.push([start, 31]);

        const next = new Map();
        for (const [lx0, lx1] of runs) {
          const runKey = lx0 + "," + lx1;
          const open = prev.get(runKey);
          if (open && open.z2 === baseZ + lz - 1) {
            open.z2 = baseZ + lz;
            next.set(runKey, open);
          } else {
            const rect = {
              x1: (baseX + lx0) * CHUNK,
              z1: (baseZ + lz) * CHUNK,
              x2: (baseX + lx1) * CHUNK + CHUNK - 1,
              z2: (baseZ + lz) * CHUNK + CHUNK - 1,
            };
            rects.push(rect);
            next.set(runKey, rect);
          }
        }
        prev = next;
      }
    }
    return { rects, chunks, times };
  }

  async function startActivityScan() {
    const dim = currentDim();
    if (!dim || state.activityBusy) return;
    const minSeconds = readActivityMinSeconds();
    if (minSeconds === null) {
      dom.activityError.textContent = "最小活动时间需要是不小于 0 的数字（单位：秒）";
      dom.activityError.hidden = false;
      return;
    }
    setActivityMinFor(dim.id, minSeconds);
    markActivityConfigChangedIfNeeded();
    state.activityBusy = true;
    dom.activityError.hidden = true;
    dom.activityProgress.hidden = false;
    dom.activityStatus.textContent =
      "正在扫描 " + dim.regionCount + " 个区域文件（" + dim.label + " · 最小 " + minSeconds + " 秒）…";
    dom.btnActivityStart.disabled = true;
    dom.btnActivityCancel.disabled = true;
    dom.btnActivityClearDiscard.disabled = true;
    dom.activityMin.disabled = true;
    try {
      const data = await api(
        "/api/activity?dim=" + encodeURIComponent(dim.id) +
          "&min=" + encodeURIComponent(String(minSeconds))
      );
      if (!data || data.dim !== dim.id || !Array.isArray(data.regions)) {
        throw new Error("服务返回的扫描结果无效");
      }
      applyActivityScan(dim, data);
    } catch (err) {
      dom.activityError.textContent = err.message || "扫描失败";
      dom.activityError.hidden = false;
    } finally {
      state.activityBusy = false;
      dom.activityProgress.hidden = true;
      dom.btnActivityStart.disabled = false;
      dom.btnActivityCancel.disabled = false;
      dom.btnActivityClearDiscard.disabled = false;
      dom.activityMin.disabled = false;
    }
  }

  function applyActivityScan(dim, data, options) {
    const silent = !!(options && options.silent);
    const discarded = new Set(discardKeys(dim.id));
    const built = activityRectsFromRegions(data.regions, discarded);
    const minSeconds = Number(data.minSeconds) || 0;
    const filterText = minSeconds > 0 ? "，最小 " + minSeconds + " 秒" : "";
    const unreadable = Number(data.unreadableChunks) || 0;
    const failed = Number(data.failedRegions) || 0;
    const tail = [];
    if (failed) tail.push(failed + " 个区域读取失败");
    if (unreadable) tail.push(unreadable + " 个区块无法解析");
    const suffix = tail.length ? "（" + tail.join("，") + "）" : "";

    const list = state.selections[dim.id] || (state.selections[dim.id] = []);
    const index = list.findIndex((sel) => sel.special === "activity");
    const existing = index >= 0 ? list[index] : null;
    const before = list.slice();
    const beforeActive = state.activeSelId;
    const finishUndo = () => {
      state.selections[dim.id] = before;
      state.activeSelId = beforeActive;
      updateActiveUI();
      persistSelections();
      renderSelections();
      updateExport();
      requestDraw();
    };

    if (!built.rects.length) {
      let reason;
      if (Number(data.activeChunks) > 0) {
        reason = "检测到的 " + data.activeChunks + " 个活跃区块都在可抛弃标记里，已全部排除";
      } else {
        reason = minSeconds > 0
          ? "没有活动时间 ≥ " + minSeconds + " 秒的区块"
          : "没有检测到玩家活动过的区块";
      }
      if (existing) {
        list.splice(index, 1);
        if (state.activeSelId === existing.id) {
          state.activeSelId = "";
          updateActiveUI();
        }
        persistSelections({ quiet: true });
        renderSelections();
        updateExport();
        requestDraw();
        if (!silent) {
          dom.activityDialog.close();
          showToast(reason + suffix + "，已移除活动选区", {
            action: "撤销",
            duration: 9000,
            onAction: finishUndo,
          });
        }
      } else if (silent) {
        showToast(reason + suffix + "。", { duration: 5600 });
      } else {
        dom.activityError.textContent = reason + suffix + "。";
        dom.activityError.hidden = false;
      }
      if (!silent) markActivityConfigChangedIfNeeded();
      return;
    }

    const updated = normalizeSelection({
      id: existing ? existing.id : uid(),
      desc: "活跃区块",
      special: "activity",
      parts: built.rects,
      activity: { chunks: built.times },
    });
    if (!updated) throw new Error("生成的选区无效");
    if (index >= 0) list[index] = updated;
    else list.push(updated);
    if (!silent) {
      state.activeSelId = updated.id;
      updateActiveUI();
    }
    persistSelections({ quiet: true });
    renderSelections();
    updateExport();
    requestDraw();
    if (silent) {
      showToast("已重新扫描活动选区 · " + built.chunks + " 个区块" + filterText + suffix, {
        duration: 5600,
      });
      return;
    }
    dom.activityDialog.close();
    showToast(
      (existing ? "已更新「" : "已生成「") + updated.desc + "」· " + built.chunks +
        " 个活跃区块" + filterText + suffix + " · 放大后右键区块可标记可抛弃",
      {
        action: "撤销",
        duration: 9000,
        onAction: finishUndo,
      }
    );
    markActivityConfigChangedIfNeeded();
  }

  function clearActivityDiscards() {
    const dim = currentDim();
    if (!dim) return;
    const count = clearDiscardKeys(dim.id);
    showToast(
      count
        ? "已清除 " + count + " 个可抛弃标记，重新扫描可恢复这些区块"
        : "本维度没有可抛弃标记",
      { duration: 5200 }
    );
    openActivityDialog();
  }

  // ---------------------------------------------------------------- export

  function selectionToPartial(dim, sel) {
    const parts = getParts(sel);
    const item = { folder: dim.folder, desc: sel.desc || "选区" };
    if (parts.length === 1) {
      item.x1 = parts[0].x1;
      item.z1 = parts[0].z1;
      item.x2 = parts[0].x2;
      item.z2 = parts[0].z2;
    } else {
      item.x1 = parts.map((part) => part.x1);
      item.z1 = parts.map((part) => part.z1);
      item.x2 = parts.map((part) => part.x2);
      item.z2 = parts.map((part) => part.z2);
    }
    return item;
  }

  function activitySelections() {
    if (!state.info) return [];
    const result = [];
    for (const dim of state.info.dimensions) {
      const sel = (state.selections[dim.id] || []).find((item) => item.special === "activity");
      if (sel) result.push({ dim, sel });
    }
    return result;
  }

  function buildPartials() {
    if (!state.info) return [];
    const items = [];
    for (const dim of state.info.dimensions) {
      const sels = state.selections[dim.id] || [];
      for (const sel of sels) {
        if (sel.special === "activity") continue;
        items.push(selectionToPartial(dim, sel));
      }
    }
    return items;
  }

  function buildActivityPartials() {
    return activitySelections()
      .filter((entry) => activityBackupOn(entry.dim.id))
      .map((entry) => selectionToPartial(entry.dim, entry.sel));
  }

  function buildBackupPartials() {
    return [...buildPartials(), ...buildActivityPartials()];
  }

  function normalizeActivityConfig(raw) {
    const map = new Map();
    const push = (folder, seconds) => {
      const key = normalizeFolder(folder);
      const value = Number(seconds);
      if (!key || !Number.isFinite(value) || value < 0) return;
      if (!map.has(key)) map.set(key, { folder: String(folder), min_seconds: Math.min(value, 365 * 86400) });
    };
    if (Array.isArray(raw)) {
      for (const item of raw) {
        if (!item || typeof item !== "object") continue;
        push(item.folder, item.min_seconds);
      }
    } else if (raw && typeof raw === "object") {
      const folders = Array.isArray(raw.folders) ? raw.folders : [];
      for (const folder of folders) push(folder, raw.min_seconds);
    }
    if (!map.size) return null;
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0])).map((pair) => pair[1]);
  }

  function buildActivityConfig() {
    const entries = activitySelections();
    if (!entries.length) return null;
    return normalizeActivityConfig(
      entries.map((entry) => ({ folder: entry.dim.folder, min_seconds: activityMinFor(entry.dim.id) }))
    );
  }

  function activityConfigEquals(a, b) {
    const left = normalizeActivityConfig(a);
    const right = normalizeActivityConfig(b);
    if (!left && !right) return true;
    if (!left || !right) return false;
    return JSON.stringify(left) === JSON.stringify(right);
  }

  function markActivityConfigChangedIfNeeded() {
    if (!state.configFile) return;
    const saved =
      state.configData && typeof state.configData === "object" ? state.configData.activity : null;
    if (activityConfigEquals(buildActivityConfig(), saved)) return;
    state.configDirty = true;
    updateConfigUI();
    cacheDraft();
  }

  function partialsCoverage(items) {
    const empty = { chunks: 0, regions: 0, existing: 0, bytes: 0, fullBytes: 0 };
    if (!state.info) return empty;
    const rectsByDim = new Map();
    for (const item of items) {
      const dim = state.info.dimensions.find((d) => d.folder === item.folder);
      if (!dim) continue;
      let rects = rectsByDim.get(dim.id);
      if (!rects) {
        rects = [];
        rectsByDim.set(dim.id, rects);
      }
      for (const raw of coordsRanges(item) || []) {
        const range = normalizeRect(raw);
        if (range) rects.push(range);
      }
    }
    const total = { ...empty };
    for (const [dimId, rects] of rectsByDim) {
      const dim = state.info.dimensions.find((d) => d.id === dimId);
      if (!dim) continue;
      const stats = rectsChunkStats(dim, rects);
      total.chunks += stats.chunks;
      total.regions += stats.regions;
      total.existing += stats.existing;
      total.bytes += stats.bytes;
      total.fullBytes += stats.fullBytes;
    }
    return total;
  }

  function normalizeIgnoreValue(value) {
    const normalized = String(value)
      .trim()
      .replace(/\\/g, "/")
      .replace(/^(?:\.?\/)+/, "")
      .replace(/\/+$/, "");
    return normalized === "." || normalized === ".." ? "" : normalized;
  }

  function normalizeIgnores(values) {
    const result = [];
    const seen = new Set();
    for (const value of values) {
      if (typeof value !== "string") continue;
      const normalized = normalizeIgnoreValue(value);
      if (!normalized) continue;
      const key = normalized.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(normalized);
    }
    return result;
  }

  function buildConfigPayload() {
    const source = state.configData && typeof state.configData === "object" ? state.configData : {};
    const cfg = { ...source };
    cfg.save_path = state.info ? state.info.path : source.save_path || "";
    cfg.ignores = [...(state.ignoreExtras || []), ...state.ignores];
    cfg.partials = [...(state.configExtras || []), ...buildPartials()];
    const activity = buildActivityConfig();
    if (activity) cfg.activity = activity;
    else delete cfg.activity;
    return cfg;
  }

  function markConfigChanged() {
    if (state.configFile) state.configDirty = true;
    cacheDraft();
  }

  function renderIgnores() {
    dom.ignoreList.replaceChildren();
    state.ignores.forEach((value, index) => {
      const chip = el("span", "ignore-chip");
      const label = el("span", "", value);
      label.title = value;
      const remove = el("button", "", "×");
      remove.type = "button";
      remove.title = "移除排除项";
      remove.setAttribute("aria-label", "移除排除项 " + value);
      remove.addEventListener("click", () => removeIgnore(index));
      chip.append(label, remove);
      dom.ignoreList.append(chip);
    });
  }

  function addIgnore() {
    const value = normalizeIgnoreValue(dom.ignoreInput.value);
    if (!value) {
      dom.ignoreInput.focus();
      return;
    }
    if (state.ignores.some((item) => item.toLowerCase() === value.toLowerCase())) {
      showToast("排除项「" + value + "」已存在");
      dom.ignoreInput.select();
      if (state.ignorePickOpen) renderIgnorePick();
      return;
    }
    state.ignores.push(value);
    dom.ignoreInput.value = "";
    closeIgnorePick();
    markConfigChanged();
    updateExport();
    showToast("已添加排除项「" + value + "」");
  }

  function removeIgnore(index, note) {
    const removed = state.ignores[index];
    if (removed === undefined) return;
    state.ignores.splice(index, 1);
    markConfigChanged();
    updateExport();
    showToast("已移除排除项「" + removed + "」" + (note || ""));
    if (state.ignorePickOpen) renderIgnorePick();
  }

  // ------------------------------------------------------------ save browser

  function loadSaveEntries(force) {
    const info = state.info;
    if (!info) return Promise.resolve(null);
    const path = info.path;
    if (!force && state.saveEntriesPath === path && state.saveEntries) {
      return Promise.resolve(state.saveEntries);
    }
    if (!force && saveEntriesPromise && state.saveEntriesPath === path) return saveEntriesPromise;
    state.saveEntriesPath = path;
    state.saveEntries = null;
    saveEntriesPromise = api("/api/entries")
      .then((data) => {
        const entries = data && Array.isArray(data.entries) ? data.entries : null;
        if (!entries) throw new Error("服务返回的目录列表无效");
        if (state.saveEntriesPath === path) {
          state.saveEntries = entries;
          state.saveEntriesTruncated = !!data.truncated;
          state.pickTree = buildEntryTree(entries);
          state.pickExpanded = new Set();
        }
        return entries;
      })
      .catch((err) => {
        showToast("读取存档目录失败：" + (err.message || "未知错误"), { error: true, duration: 5200 });
        return null;
      })
      .finally(() => {
        saveEntriesPromise = null;
      });
    return saveEntriesPromise;
  }

  function pickQuery() {
    return normalizeIgnoreValue(dom.ignoreInput.value).toLowerCase();
  }

  function buildEntryTree(entries) {
    const root = { path: "", name: "", depth: 0, type: "dir", children: [] };
    const map = new Map([["", root]]);
    entries.forEach((item) => {
      const path = normalizeIgnoreValue(item.path);
      if (!path) return;
      const cut = path.lastIndexOf("/");
      const parent = map.get(cut < 0 ? "" : path.slice(0, cut));
      if (!parent) return;
      const node = {
        path,
        name: cut < 0 ? path : path.slice(cut + 1),
        depth: parent.depth + 1,
        type: item.type === "dir" ? "dir" : "file",
        children: [],
        hit: false,
        subHit: false,
      };
      parent.children.push(node);
      if (node.type === "dir") map.set(path, node);
    });
    const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });
    map.forEach((node) => {
      node.children.sort(
        (a, b) => (b.type === "dir") - (a.type === "dir") || collator.compare(a.name, b.name)
      );
    });
    return { root, map };
  }

  function markPickHits(node, query) {
    let childHit = false;
    node.children.forEach((child) => {
      if (markPickHits(child, query)) childHit = true;
    });
    node.hit =
      node.name.toLowerCase().includes(query) || node.path.toLowerCase().includes(query);
    node.subHit = childHit;
    return node.hit || childHit;
  }

  function computePickRows() {
    const tree = state.pickTree;
    if (!tree) return { rows: [], matched: 0, query: "" };
    const query = pickQuery();
    const rows = [];
    if (!query) {
      const expanded = state.pickExpanded || new Set();
      const walk = (node) => {
        node.children.forEach((child) => {
          const open = child.type === "dir" && !!child.children.length && expanded.has(child.path);
          rows.push({ node: child, context: false, open });
          if (open) walk(child);
        });
      };
      walk(tree.root);
      return { rows, matched: 0, query };
    }
    let matched = 0;
    markPickHits(tree.root, query);
    const countHits = (node) => {
      node.children.forEach((child) => {
        if (child.hit) matched += 1;
        countHits(child);
      });
    };
    countHits(tree.root);
    const walk = (node) => {
      node.children.forEach((child) => {
        if (!child.hit && !child.subHit) return;
        const open = child.type === "dir" && child.subHit;
        rows.push({ node: child, context: !child.hit, open });
        if (open) walk(child);
      });
    };
    walk(tree.root);
    return { rows, matched, query };
  }

  function ignoreIndexOf(path) {
    const lower = normalizeIgnoreValue(path).toLowerCase();
    return state.ignores.findIndex(
      (value) => normalizeIgnoreValue(value).toLowerCase() === lower
    );
  }

  function excludedAncestorOf(path) {
    const lower = normalizeIgnoreValue(path).toLowerCase();
    let best = null;
    state.ignores.forEach((value, index) => {
      const ig = normalizeIgnoreValue(value);
      if (!ig || ig.toLowerCase() === lower) return;
      if (!lower.startsWith(ig.toLowerCase() + "/")) return;
      if (!best || ig.length > best.value.length) best = { index, value: ig };
    });
    return best;
  }

  function renderIgnorePick() {
    const result = computePickRows();
    const rows = result.rows;
    const total = (state.saveEntries || []).length;
    state.pickRows = rows;
    if (state.pickCursor >= rows.length) state.pickCursor = rows.length - 1;
    const shown = rows.slice(0, PICK_RENDER_LIMIT);
    dom.ignorePickList.replaceChildren();
    if (!shown.length) {
      dom.ignorePickList.append(
        el(
          "p",
          "pick-empty",
          state.saveEntries
            ? "没有匹配的路径。可直接输入相对路径后点「添加」。"
            : "正在读取存档目录…"
        )
      );
    }
    shown.forEach((row, index) => {
      const node = row.node;
      const direct = ignoreIndexOf(node.path) >= 0;
      const inherited = direct ? null : excludedAncestorOf(node.path);
      const classes = ["pick-item"];
      if (node.type === "dir") classes.push("dir");
      if (direct) classes.push("on");
      if (inherited) classes.push("inh");
      if (row.context) classes.push("ctx");
      const item = el("button", classes.join(" "));
      item.type = "button";
      item.style.paddingLeft = 4 + (node.depth - 1) * 12 + "px";
      const twisty = el("span", "pick-twisty");
      const foldable = node.type === "dir" && !!node.children.length;
      if (foldable) {
        twisty.innerHTML = icons.chevron;
        twisty.dataset.open = row.open ? "1" : "0";
      }
      const icon = el("span", "pick-icon");
      icon.innerHTML = node.type === "dir" ? icons.folder : icons.file;
      const kind = el(
        "span",
        "pick-kind",
        direct ? "已排除" : inherited ? "随父排除" : node.type === "dir" ? "目录" : "文件"
      );
      item.append(twisty, icon, el("span", "pick-path", node.name), kind);
      item.title =
        node.path +
        " · " +
        (direct
          ? "点击移出排除项"
          : inherited
          ? "已随「" + inherited.value + "」排除 · 点击取消排除「" + inherited.value + "」"
          : "点击加入排除项" + (foldable ? " · 点箭头展开/折叠" : ""));
      if (index === state.pickCursor) item.classList.add("cursor");
      item.addEventListener("click", (event) => {
        if (event.target.closest(".pick-twisty")) togglePickExpand(node);
        else toggleIgnorePath(node.path);
      });
      dom.ignorePickList.append(item);
    });
    if (rows.length > shown.length) {
      dom.ignorePickList.append(
        el("p", "pick-empty", "仅显示前 " + PICK_RENDER_LIMIT + " 行，继续输入可缩小范围。")
      );
    }
    dom.ignorePickNote.textContent = state.saveEntries
      ? (result.query
          ? "匹配 " + result.matched + " / " + total + " 项 · 自动展开命中目录"
          : total + " 项 · 点箭头展开，点行加入或移出") +
        (state.saveEntriesTruncated ? " · 目录过大已截断" : "")
      : "正在读取存档目录…";
  }

  function togglePickExpand(node) {
    if (pickQuery() || !node || node.type !== "dir" || !node.children.length) return;
    if (!state.pickExpanded) state.pickExpanded = new Set();
    if (state.pickExpanded.has(node.path)) state.pickExpanded.delete(node.path);
    else state.pickExpanded.add(node.path);
    const keepCursor =
      state.pickCursor >= 0 &&
      state.pickRows[state.pickCursor] &&
      state.pickRows[state.pickCursor].node.path === node.path;
    state.pickCursor = -1;
    renderIgnorePick();
    if (keepCursor) movePickCursorTo(node.path);
  }

  function toggleIgnorePath(path) {
    const index = ignoreIndexOf(path);
    if (index >= 0) {
      removeIgnore(index);
      return;
    }
    const inherited = excludedAncestorOf(path);
    if (inherited) {
      removeIgnore(inherited.index, "，「" + normalizeIgnoreValue(path) + "」恢复备份");
      return;
    }
    state.ignores.push(normalizeIgnoreValue(path));
    markConfigChanged();
    updateExport();
    renderIgnorePick();
    showToast("已添加排除项「" + path + "」", { duration: 2800 });
  }

  function openIgnorePick() {
    if (!state.info) {
      showToast("请先加载存档", { error: true });
      return;
    }
    state.ignorePickOpen = true;
    state.pickCursor = -1;
    dom.ignorePick.hidden = false;
    dom.btnIgnoreBrowse.classList.add("active");
    renderIgnorePick();
    loadSaveEntries(false).then(() => {
      if (state.ignorePickOpen) renderIgnorePick();
    });
    dom.ignoreInput.focus();
  }

  function closeIgnorePick() {
    if (!state.ignorePickOpen) return;
    state.ignorePickOpen = false;
    state.pickCursor = -1;
    dom.ignorePick.hidden = true;
    dom.btnIgnoreBrowse.classList.remove("active");
  }

  function scrollPickCursor() {
    const row = dom.ignorePickList.querySelector(".pick-item.cursor");
    if (row) row.scrollIntoView({ block: "nearest" });
  }

  function movePickCursor(delta) {
    const count = Math.min(state.pickRows.length, PICK_RENDER_LIMIT);
    if (!count) return;
    state.pickCursor = clamp((state.pickCursor < 0 ? -1 : state.pickCursor) + delta, 0, count - 1);
    renderIgnorePick();
    scrollPickCursor();
  }

  function movePickCursorTo(path) {
    const index = state.pickRows.findIndex((row) => row.node.path === path);
    if (index < 0) return;
    state.pickCursor = index;
    renderIgnorePick();
    scrollPickCursor();
  }

  function onIgnoreInput() {
    state.pickCursor = -1;
    if (state.ignorePickOpen) {
      renderIgnorePick();
    } else if (state.info && dom.ignoreInput.value.trim()) {
      openIgnorePick();
    }
  }

  function onIgnoreInputKeydown(event) {
    if (!state.ignorePickOpen) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      movePickCursor(event.key === "ArrowDown" ? 1 : -1);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeIgnorePick();
      return;
    }
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const row = state.pickRows[state.pickCursor];
      if (!row) return;
      event.preventDefault();
      const foldable = row.node.type === "dir" && !!row.node.children.length;
      if (event.key === "ArrowLeft") {
        if (row.open) togglePickExpand(row.node);
        else {
          const cut = row.node.path.lastIndexOf("/");
          if (cut > 0) movePickCursorTo(row.node.path.slice(0, cut));
        }
        return;
      }
      if (!foldable) return;
      if (!row.open) togglePickExpand(row.node);
      else {
        state.pickCursor = clamp(state.pickCursor + 1, 0, state.pickRows.length - 1);
        renderIgnorePick();
        scrollPickCursor();
      }
      return;
    }
    if (event.key === "Enter" && state.pickCursor >= 0) {
      const row = state.pickRows[state.pickCursor];
      if (row) {
        event.preventDefault();
        toggleIgnorePath(row.node.path);
      }
    }
  }

  function resetSaveEntries() {
    closeIgnorePick();
    state.saveEntries = null;
    state.saveEntriesPath = "";
    state.saveEntriesTruncated = false;
    state.pickTree = null;
    state.pickExpanded = new Set();
    state.pickRows = [];
    state.pickCursor = -1;
  }

  function updateExport() {
    updateConfigUI();
    renderIgnores();
    const hasWorld = !!state.info;
    dom.btnPreview.disabled = !hasWorld;
    dom.btnCopy.disabled = !hasWorld;
    dom.btnDownload.disabled = !hasWorld;
    if (!hasWorld) {
      dom.exportPreview.value = "{}";
      dom.exportStats.textContent = "加载存档后可预览和保存完整配置。";
      return;
    }
    dom.exportPreview.value = JSON.stringify(buildConfigPayload(), null, 2);
    const items = buildBackupPartials();
    if (!items.length) {
      dom.exportStats.textContent = "全部维度暂无选区；仍可预览或保存配置。";
      return;
    }
    const coverage = partialsCoverage(items);
    dom.exportStats.textContent =
      "全部维度 " +
      items.length +
      " 条选区 · 覆盖 " +
      coverage.chunks +
      " 个区块（" +
      coverage.existing +
      " 个已生成 · 约 " +
      formatBytes(coverage.bytes) +
      "）";
  }

  function openPreviewDialog() {
    if (!state.info) return;
    updateExport();
    const items = buildBackupPartials();
    const ignoreCount = state.ignores.length;
    dom.previewSub.textContent =
      "完整配置 · " +
      items.length +
      " 条选区" +
      (ignoreCount ? " · " + ignoreCount + " 个排除项" : "");
    if (!dom.previewDialog.open) dom.previewDialog.showModal();
    dom.exportPreview.scrollTop = 0;
    dom.exportPreview.scrollLeft = 0;
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {}
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (err2) {
      ok = false;
    }
    area.remove();
    return ok;
  }

  async function copyExport() {
    if (dom.btnCopy.disabled) return;
    const ok = await copyText(dom.exportPreview.value);
    showToast(ok ? "配置已复制到剪贴板" : "复制失败，请手动选择文本复制", { error: !ok });
  }

  function downloadExport() {
    if (dom.btnDownload.disabled) return;
    const text = dom.exportPreview.value + "\n";
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const fallback = (((state.info && state.info.name) || "world") + "-config.json");
    const name = (state.configFile || fallback).replace(/[\\/:*?"<>|]+/g, "_");
    link.href = url;
    link.download = name;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    showToast("已下载 JSON 文件");
  }

  // ---------------------------------------------------------------- config

  function normalizeFolder(value) {
    return String(value || "")
      .replace(/\\/g, "/")
      .replace(/^\.\//, "")
      .replace(/\/+$/, "")
      .toLowerCase();
  }

  function dimByFolder(folder) {
    if (!state.info) return null;
    const key = normalizeFolder(folder);
    const direct = state.info.dimensions.find((dim) => normalizeFolder(dim.folder) === key);
    if (direct) return direct;
    const dimId = LEGACY_FOLDER_DIM[key];
    return dimId ? state.info.dimensions.find((dim) => dim.id === dimId) || null : null;
  }

  function folderListOf(item) {
    const value = item.folder !== undefined ? item.folder : item.folders;
    if (typeof value === "string") return [value];
    if (Array.isArray(value)) return value.filter((v) => typeof v === "string");
    return [];
  }

  function coordsRanges(item) {
    const { x1, z1, x2, z2 } = item;
    if ([x1, z1, x2, z2].every(Number.isFinite)) {
      return [{ x1, z1, x2, z2 }];
    }
    if (![x1, z1, x2, z2].every(Array.isArray)) return null;
    const n = Math.min(x1.length, z1.length, x2.length, z2.length);
    if (!n || x1.length !== z1.length || x1.length !== x2.length || x1.length !== z2.length) {
      return null;
    }
    const ranges = [];
    for (let i = 0; i < n; i += 1) {
      const range = { x1: x1[i], z1: z1[i], x2: x2[i], z2: z2[i] };
      if ([range.x1, range.z1, range.x2, range.z2].every(Number.isFinite)) ranges.push(range);
    }
    return ranges.length ? ranges : null;
  }

  function selectionsFromConfig(config) {
    const result = {};
    const extras = [];
    const seenByDim = {};
    let counter = 0;
    const parts = config && Array.isArray(config.partials) ? config.partials : [];
    for (const item of parts) {
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        extras.push(item);
        continue;
      }
      if (item.files !== undefined) {
        extras.push(item);
        continue;
      }
      const folders = folderListOf(item);
      if (!folders.length) {
        extras.push(item);
        continue;
      }
      const ranges = coordsRanges(item);
      if (!ranges) {
        extras.push(item);
        continue;
      }
      const mapped = folders
        .map((folder) => ({ folder, dim: dimByFolder(folder) }))
        .filter((entry) => entry.dim);
      if (!mapped.length) {
        extras.push(item);
        continue;
      }
      const unknownFolders = folders.filter((folder) => !dimByFolder(folder));
      if (unknownFolders.length) {
        extras.push({ ...item, folder: unknownFolders.length === 1 ? unknownFolders[0] : unknownFolders });
      }
      const baseDesc = typeof item.desc === "string" && item.desc.trim() ? item.desc.trim() : "";
      for (const { dim } of mapped) {
        counter += 1;
        let desc = baseDesc || "选区 " + counter;
        if (mapped.length > 1) desc += " · " + dim.label;
        const sel = normalizeSelection({ id: uid(), desc, parts: ranges });
        if (!sel) continue;
        const seen = seenByDim[dim.id] || (seenByDim[dim.id] = new Set());
        const key = selectionSignature(sel);
        if (seen.has(key)) continue;
        seen.add(key);
        if (!result[dim.id]) result[dim.id] = [];
        result[dim.id].push(sel);
      }
    }
    return { selections: result, extras };
  }

  function updateConfigUI() {
    const hasSel = totalSelectionCount() > 0;
    if (state.configFile) {
      dom.configName.textContent = state.configFile + (state.configDirty ? " · 未保存" : "");
      dom.configName.classList.toggle("dirty", state.configDirty);
      dom.configName.title =
        state.configFile + (state.configDirty ? " · 有未保存的配置修改" : " · 已保存");
    } else {
      dom.configName.textContent = hasSel ? "未关联（临时选区）" : "未关联";
      dom.configName.classList.remove("dirty");
      dom.configName.title = hasSel ? "保存到 configs 后可直接备份" : "加载已有配置或框选区块";
    }
    updateBackupUI();
  }

  function updateBackupUI() {
    const job = state.backupJob;
    const running = !!(job && job.running);
    const hasSel = totalSelectionCount() > 0;
    const showResult = !running && state.backupUnseen;
    dom.btnBackup.disabled = !state.info || (!hasSel && !running && !showResult);
    dom.btnBackupText.textContent = running
      ? "备份中… · 查看进度"
      : showResult
        ? "备份完成 · 查看结果"
        : "开始备份";
    dom.btnBackup.classList.toggle("running", running || showResult);
    dom.btnBackup.title = !state.info
      ? "先加载存档"
      : !hasSel && !running && !showResult
        ? "先框选至少一个区块"
        : state.configDirty
          ? "配置有未保存修改，开始备份前会提示保存"
          : "";
  }

  function showConfigError(message) {
    dom.configError.textContent = message;
    dom.configError.hidden = false;
  }

  function setConfigBusy(busy) {
    dom.configSelect.disabled = busy;
    dom.btnConfigLoad.disabled = busy || !dom.configSelect.value;
    dom.btnConfigSave.disabled = busy || !state.info;
    dom.btnConfigSave.textContent = busy ? "处理中…" : "保存配置";
  }

  function configSelectionCount(item) {
    return (Number(item.partialCount) || 0) + (Number(item.activityCount) || 0);
  }

  function fillConfigSelect() {
    const select = dom.configSelect;
    select.replaceChildren();
    select.append(
      new Option(state.configList.length ? "选择已有配置…" : "configs 目录中没有配置", "")
    );
    for (const item of state.configList) {
      const suffix = item.error ? "读取失败" : configSelectionCount(item) + " 条选区";
      select.append(new Option(item.file + " · " + suffix, item.file));
    }
    const preferred = state.configFile || state.lastConfigFile;
    if (preferred && state.configList.some((item) => item.file === preferred)) {
      select.value = preferred;
    } else if (state.configList.length === 1 && !state.configList[0].error) {
      select.value = state.configList[0].file;
    }
  }

  function updateConfigHint() {
    const item = state.configList.find((c) => c.file === dom.configSelect.value);
    if (!item) {
      dom.configHint.textContent =
        "选择已有配置加载到地图；或在下面输入文件名，把当前选区另存为新配置。";
      dom.btnConfigLoad.disabled = true;
      return;
    }
    if (item.error) {
      dom.configHint.textContent = "读取失败：" + item.error;
      dom.btnConfigLoad.disabled = true;
      return;
    }
    dom.configHint.textContent =
      (item.savePath || "缺少 save_path") + " · " + configSelectionCount(item) + " 条区域配置";
    dom.btnConfigLoad.disabled = false;
  }

  async function openConfigDialog(preferSave) {
    dom.configError.hidden = true;
    dom.configNewName.value = "";
    dom.configSelect.disabled = true;
    dom.btnConfigLoad.disabled = true;
    dom.btnConfigSave.disabled = true;
    dom.btnConfigSave.title = state.info ? "" : "先加载存档";
    dom.configSelect.replaceChildren(new Option("正在读取 configs…", ""));
    dom.configHint.textContent = "正在读取配置目录…";
    if (!dom.configDialog.open) dom.configDialog.showModal();
    try {
      const data = await api("/api/configs");
      state.configList = Array.isArray(data.configs) ? data.configs : [];
    } catch (err) {
      state.configList = [];
      dom.configHint.textContent = "无法读取配置目录：" + err.message;
    }
    fillConfigSelect();
    dom.configSelect.disabled = false;
    updateConfigHint();
    dom.btnConfigSave.disabled = !state.info;
    window.setTimeout(() => {
      if (preferSave) dom.configNewName.focus();
      else dom.configSelect.focus();
    }, 30);
  }

  async function loadConfigFile(file) {
    const res = await api("/api/configs/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file }),
    });
    const parsed = applyLoadedConfig(res);
    return { res, parsed };
  }

  function applyLoadedConfig(res) {
    if (!isWorldInfo(res.world)) throw new Error("服务返回的存档数据无效");
    applyWorld(res.world);
    const parsed = selectionsFromConfig(res.config || {});
    state.configFile = "";
    state.selections = parsed.selections;
    state.selStore[res.world.path] = state.selections;
    persistSelections();
    state.configFile = res.file;
    state.configData = res.config || {};
    state.configExtras = parsed.extras;
    const ignoreItems = Array.isArray(state.configData.ignores) ? state.configData.ignores : [];
    state.ignoreExtras = ignoreItems.filter((item) => typeof item !== "string");
    state.ignores = normalizeIgnores(ignoreItems);
    const activityConfig = normalizeActivityConfig(state.configData.activity);
    if (activityConfig) {
      for (const entry of activityConfig) {
        const dim = dimByFolder(entry.folder);
        if (dim) state.activityMinByDim[dim.id] = entry.min_seconds;
      }
    }
    state.configDirty = false;
    state.configWorldPath = res.world.path;
    state.lastConfigFile = res.file;
    saveSettings();

    const dimWithSel = res.world.dimensions.find(
      (dim) => (parsed.selections[dim.id] || []).length > 0
    );
    if (dimWithSel && !(parsed.selections[state.dim] || []).length) {
      state.dim = dimWithSel.id;
      state.hasView = false;
      state.autoFit = true;
      renderDims();
      fitView();
    }
    renderSelections();
    updateExport();
    updateConfigUI();
    clearDraft();
    requestDraw();
    if (activityConfig) {
      const targets = activityTargetsFromConfig(activityConfig);
      if (targets.length) rescanActivityFromConfig(targets);
    }
    return parsed;
  }

  function activityTargetsFromConfig(entries) {
    const targets = [];
    const seen = new Set();
    for (const entry of entries) {
      const dim = dimByFolder(entry.folder);
      if (!dim || seen.has(dim.id)) continue;
      seen.add(dim.id);
      targets.push({ dim, minSeconds: entry.min_seconds });
    }
    return targets;
  }

  function maybePromptActivityScan(info) {
    if (state.configFile || !info || !Array.isArray(info.dimensions)) return;
    const targets = info.dimensions.filter(
      (dim) =>
        dim.regionCount > 0 &&
        !(state.selections[dim.id] || []).some((sel) => sel.special === "activity")
    );
    if (!targets.length) return;
    state.activityPromptTargets = targets;
    dom.activityPromptDims.textContent = targets.map((dim) => dim.label).join("、");
    if (!dom.activityPromptDialog.open) dom.activityPromptDialog.showModal();
  }

  function closeActivityPrompt() {
    state.activityPromptTargets = null;
    dom.activityPromptDialog.close();
  }

  function runActivityPromptScan() {
    const dims = state.activityPromptTargets || [];
    closeActivityPrompt();
    if (!dims.length) return;
    showToast("正在扫描 " + dims.length + " 个维度的活跃区块…", { duration: 4200 });
    rescanActivityFromConfig(
      dims.map((dim) => ({ dim, minSeconds: activityMinFor(dim.id) }))
    );
  }

  async function rescanActivityFromConfig(targets) {
    const token = state.token;
    for (const target of targets) {
      const dim = target.dim;
      const minSeconds = target.minSeconds;
      try {
        const data = await api(
          "/api/activity?dim=" + encodeURIComponent(dim.id) +
            "&min=" + encodeURIComponent(String(minSeconds))
        );
        if (token !== state.token || activityMinFor(dim.id) !== minSeconds) return;
        if (!data || data.dim !== dim.id || !Array.isArray(data.regions)) {
          throw new Error("服务返回的扫描结果无效");
        }
        applyActivityScan(dim, data, { silent: true });
      } catch (err) {
        if (token === state.token) {
          showToast(
            "活动选区重新扫描失败（" + dim.label + "）：" + (err.message || "未知错误"),
            { error: true, duration: 6500 }
          );
        }
      }
    }
  }

  async function loadConfigFromDialog() {
    const file = dom.configSelect.value;
    if (!file) {
      showConfigError("请选择一个已有配置");
      return;
    }
    const item = state.configList.find((c) => c.file === file);
    if (item && item.error) {
      showConfigError("该配置读取失败：" + item.error);
      return;
    }
    const total = totalSelectionCount();
    if (total && !window.confirm("加载配置会替换当前地图上的 " + total + " 个选区，继续吗？")) {
      return;
    }
    dom.configError.hidden = true;
    setConfigBusy(true);
    try {
      const { res, parsed } = await loadConfigFile(file);
      dom.configDialog.close();
      showToast(
        "已加载「" + res.file + "」 · " + totalSelectionCount() + " 个选区" +
          (parsed.extras.length ? " · 保留 " + parsed.extras.length + " 条非区域项" : ""),
        { duration: 5200 }
      );
    } catch (err) {
      showConfigError(err.message || "加载配置失败");
    } finally {
      setConfigBusy(false);
      updateConfigHint();
    }
  }

  async function saveConfigTo(file) {
    if (!state.info) throw new Error("尚未加载存档");
    const cfg = buildConfigPayload();
    const res = await api("/api/configs/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file, config: cfg }),
    });
    state.configData = cfg;
    state.configFile = res.file;
    state.configDirty = false;
    state.configWorldPath = state.info.path;
    state.lastConfigFile = res.file;
    saveSettings();
    updateExport();
    clearDraft();
    const activityCount = Array.isArray(cfg.activity) ? cfg.activity.length : 0;
    return {
      res,
      count: cfg.partials.length - (state.configExtras || []).length + activityCount,
    };
  }

  async function saveConfigFromDialog(event) {
    event.preventDefault();
    if (!state.info) {
      showConfigError("请先加载存档");
      return;
    }
    const file = dom.configNewName.value.trim() || dom.configSelect.value;
    if (!file) {
      showConfigError("请选择已有配置，或在下面输入一个新文件名");
      return;
    }
    dom.configError.hidden = true;
    setConfigBusy(true);
    try {
      const { res, count } = await saveConfigTo(file);
      dom.configDialog.close();
      const backupNote = res.backupFile ? "；原文件已备份为 " + res.backupFile : "";
      const ignoreNote = state.ignores.length ? " · " + state.ignores.length + " 个排除项" : "";
      showToast(
        "已保存「" + res.file + "」 · " + count + " 条选区" + ignoreNote + backupNote,
        { duration: 6000 }
      );
    } catch (err) {
      showConfigError(err.message || "保存配置失败");
    } finally {
      setConfigBusy(false);
      updateConfigHint();
    }
  }

  // ---------------------------------------------------------------- backup

  function addBackupRow(key, value) {
    dom.backupSummary.append(el("span", "k", key), el("span", "v", String(value)));
  }

  function updateBackupSavePrompt() {
    const dirty = !!(state.configFile && state.configDirty);
    dom.backupSavePrompt.hidden = !dirty;
    if (dirty) {
      dom.backupSaveHint.textContent =
        "「" + state.configFile + "」有未保存的配置修改，可以立即保存，或直接开始备份。";
    }
    dom.btnBackupStart.textContent = dirty ? "保存并开始备份" : "开始备份";
  }

  function renderBackupSummary(items, coverage) {
    dom.backupSummary.replaceChildren();
    addBackupRow("配置文件", state.configFile);
    addBackupRow("存档", (state.info.name || "存档") + " · " + state.info.path);
    addBackupRow(
      "选区",
      items.length + " 条 · 覆盖 " + coverage.chunks + " 个区块 · " + coverage.regions +
        " 个区域文件（" + coverage.existing + " 个区块已生成）"
    );
    addBackupRow(
      "备份方式",
      state.chunkOnlyBackup ? "仅保存选中区块（裁剪区域文件）" : "保留完整区域文件（默认）"
    );
    addBackupRow(
      "预计大小",
      state.chunkOnlyBackup
        ? "约 " + formatBytes(coverage.bytes) + "（按选中区块裁剪后估算）"
        : "选区区域约 " + formatBytes(coverage.fullBytes) + "（完整区域文件）"
    );
    if (state.ignores.length) addBackupRow("排除项", state.ignores.join("、"));
    addBackupRow("输出", "zip 生成在存档文件夹旁，文件名带时间戳");
  }

  function backupWarningText(coverage) {
    let warning;
    if (state.chunkOnlyBackup) {
      warning =
        "开启「仅保存选中的区块」后会重建区域文件，只保留选中的 " +
        coverage.existing +
        " 个已生成区块；裁剪后的区域文件尚未经过长期验证，建议先保留一份完整备份。";
      const missing = coverage.chunks - coverage.existing;
      if (missing > 0) warning += " 选区中有 " + missing + " 个区块尚未生成，备份时会自动跳过。";
    } else {
      warning =
        "默认会保留选区涉及的完整区域文件（.mca），不裁剪区块数据，兼容性最好，但体积会比仅保存区块大。";
    }
    return warning + " 建议先关闭 Minecraft，避免复制到正在写入的文件。";
  }

  function updateChunkOnlyUI() {
    dom.chunkOnlyToggle.checked = state.chunkOnlyBackup;
    dom.chunkOnlyHint.textContent = state.chunkOnlyBackup
      ? "会重建区域文件，只保留选中的区块；体积更小，但属于实验性裁剪。"
      : "默认关闭：保留选区涉及的完整区域文件，最安全。";
    if (!state.backupCoverage) return;
    renderBackupSummary(state.backupItems || [], state.backupCoverage);
    dom.backupWarning.textContent = backupWarningText(state.backupCoverage);
  }

  function onChunkOnlyToggle() {
    state.chunkOnlyBackup = dom.chunkOnlyToggle.checked;
    saveSettings();
    updateChunkOnlyUI();
  }

  function showBackupConfirm() {
    state.backupPollErrors = 0;
    const items = buildBackupPartials();
    const coverage = partialsCoverage(items);
    state.backupCoverage = coverage;
    state.backupItems = items;
    dom.backupTitle.textContent = "开始备份";
    dom.backupSub.textContent = state.configFile + (state.configDirty ? " · 有未保存修改" : "");
    dom.backupSummary.hidden = false;
    dom.backupNoteWrap.hidden = false;
    dom.backupNote.disabled = false;
    dom.backupOption.hidden = false;
    updateChunkOnlyUI();
    dom.backupWarning.hidden = false;
    dom.backupProgress.hidden = true;
    dom.backupError.hidden = true;
    dom.backupLog.hidden = true;
    dom.backupLog.textContent = "";
    dom.btnBackupStart.hidden = false;
    dom.btnBackupStart.disabled = false;
    dom.btnBackupQuickSave.hidden = false;
    dom.btnBackupQuickSave.disabled = false;
    dom.btnBackupQuickSave.textContent = "立即保存";
    dom.btnBackupClose.textContent = "取消";
    dom.btnBackupCopyZip.hidden = true;
    updateBackupSavePrompt();
  }

  function openBackupDialog() {
    if (!state.info) {
      showToast("请先加载存档", { error: true });
      return;
    }
    if (state.backupJob && (state.backupJob.running || state.backupUnseen)) {
      renderBackupJob(state.backupJob);
      if (!dom.backupDialog.open) dom.backupDialog.showModal();
      if (state.backupJob.running) pollBackup();
      return;
    }
    if (!totalSelectionCount()) {
      showToast("先框选至少一个区块", { error: true });
      return;
    }
    if (!state.configFile) {
      showToast("先保存备份配置，然后即可开始备份");
      openConfigDialog(true);
      return;
    }
    dom.backupNote.value = "";
    showBackupConfirm();
    if (!dom.backupDialog.open) dom.backupDialog.showModal();
  }

  async function quickSaveBackupConfig() {
    if (!state.configFile || !state.configDirty) return;
    dom.backupError.hidden = true;
    dom.btnBackupQuickSave.disabled = true;
    dom.btnBackupStart.disabled = true;
    dom.btnBackupQuickSave.textContent = "保存中…";
    try {
      await saveConfigTo(state.configFile);
      updateBackupSavePrompt();
      dom.backupSub.textContent = state.configFile;
      dom.backupError.hidden = true;
      showToast("配置已保存，可以开始备份");
    } catch (err) {
      dom.backupError.textContent = err.message || "保存配置失败";
      dom.backupError.hidden = false;
    } finally {
      dom.btnBackupQuickSave.disabled = false;
      dom.btnBackupStart.disabled = false;
      dom.btnBackupQuickSave.textContent = "立即保存";
    }
  }

  async function startBackup() {
    if (!state.info) return;
    if (!state.configFile) {
      openConfigDialog(true);
      return;
    }
    dom.backupError.hidden = true;
    dom.btnBackupStart.disabled = true;
    dom.btnBackupStart.textContent = "正在准备…";
    try {
      if (state.configDirty) await saveConfigTo(state.configFile);
      dom.backupTitle.textContent = "正在备份";
      dom.backupSub.textContent = state.configFile;
      const note = dom.backupNote.value.trim();
      dom.backupSummary.hidden = true;
      dom.backupNoteWrap.hidden = true;
      dom.backupOption.hidden = true;
      dom.backupSavePrompt.hidden = true;
      dom.backupWarning.hidden = true;
      dom.backupProgress.hidden = false;
      dom.backupStatus.textContent = "正在启动备份…";
      dom.backupLog.hidden = false;
      dom.backupLog.textContent = "正在启动备份进程…";
      dom.btnBackupClose.textContent = "后台运行";
      dom.btnBackupStart.hidden = true;
      dom.btnBackupCopyZip.hidden = true;
      const data = await api("/api/backup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file: state.configFile,
          chunk_only: state.chunkOnlyBackup,
          note,
          extra_partials: buildActivityPartials(),
        }),
      });
      if (!data.job) throw new Error("服务没有返回备份任务");
      state.backupJob = data.job;
      state.backupPollErrors = 0;
      state.backupUnseen = false;
      renderBackupJob(state.backupJob);
      updateConfigUI();
      if (state.backupJob.running) pollBackup();
      else finishBackup(state.backupJob);
    } catch (err) {
      showBackupConfirm();
      dom.backupError.textContent = err.message || "无法启动备份";
      dom.backupError.hidden = false;
    }
  }

  function renderBackupJob(job) {
    if (!job) return;
    const running = !!job.running;
    dom.backupSummary.hidden = running;
    dom.backupNoteWrap.hidden = true;
    dom.backupOption.hidden = true;
    dom.backupSavePrompt.hidden = true;
    dom.backupWarning.hidden = true;
    dom.backupError.hidden = true;
    dom.backupLog.hidden = false;
    const log = dom.backupLog;
    const stick = log.scrollHeight - log.scrollTop - log.clientHeight < 48;
    log.textContent =
      job.lines && job.lines.length
        ? job.lines.join("\n")
        : running
          ? "等待备份进程输出…"
          : "没有输出。";
    if (stick) log.scrollTop = log.scrollHeight;

    if (running) {
      dom.backupTitle.textContent = "正在备份";
      dom.backupSub.textContent = job.file + " · 可以关闭窗口，备份会在后台继续";
      dom.backupProgress.hidden = false;
      const elapsed = Math.max(0, Math.round(Date.now() / 1000 - job.started));
      dom.backupStatus.textContent = "正在复制并打包… 已用 " + elapsed + " 秒";
      dom.btnBackupStart.hidden = true;
      dom.btnBackupCopyZip.hidden = true;
      dom.btnBackupClose.textContent = "后台运行";
      return;
    }

    const ok = !!job.zipPath;
    dom.backupProgress.hidden = true;
    dom.backupTitle.textContent = ok ? "备份完成" : "备份失败";
    dom.backupSub.textContent = job.file;
    dom.backupSummary.hidden = false;
    dom.backupSummary.replaceChildren();
    addBackupRow("配置文件", job.file);
    if (job.note) addBackupRow("备注", job.note);
    if (ok) {
      addBackupRow("输出文件", job.zipPath);
      addBackupRow("大小", formatBytes(job.zipSize));
    } else {
      addBackupRow("结果", job.error || "备份进程结束，但没有找到生成的 zip 文件");
    }
    if (job.started && job.finished) addBackupRow("用时", formatDuration(job.finished - job.started));
    dom.btnBackupStart.hidden = true;
    dom.btnBackupCopyZip.hidden = !ok;
    dom.btnBackupClose.textContent = "关闭";
  }

  function pollBackup() {
    clearTimeout(state.backupTimer);
    state.backupTimer = null;
    if (!state.backupJob || !state.backupJob.running) return;
    state.backupTimer = window.setTimeout(fetchBackupStatus, 850);
  }

  async function fetchBackupStatus() {
    if (!state.backupJob) return;
    try {
      const data = await api("/api/backup/status");
      const job = data.job;
      if (!job || job.id !== state.backupJob.id) throw new Error("找不到备份任务");
      const wasRunning = state.backupJob.running;
      state.backupJob = job;
      if (dom.backupDialog.open) renderBackupJob(job);
      updateBackupUI();
      if (job.running) {
        state.backupPollErrors = 0;
        pollBackup();
      } else if (wasRunning) {
        finishBackup(job);
      }
    } catch (err) {
      state.backupPollErrors += 1;
      if (state.backupPollErrors < 6) {
        state.backupTimer = window.setTimeout(fetchBackupStatus, 1500);
      } else {
        showToast("无法获取备份进度：" + err.message, { error: true, duration: 5000 });
      }
    }
  }

  function finishBackup(job) {
    clearTimeout(state.backupTimer);
    state.backupTimer = null;
    if (!dom.backupDialog.open) state.backupUnseen = true;
    updateBackupUI();
    if (job.zipPath) {
      showToast("备份完成：" + job.zipPath, { duration: 7000 });
    } else {
      showToast(job.error || "备份结束，但没有生成 zip 文件", { error: true, duration: 7000 });
    }
  }

  function onBackupDialogClose() {
    if (state.backupJob && !state.backupJob.running) {
      state.backupJob = null;
      state.backupUnseen = false;
      updateBackupUI();
    }
  }

  async function loadBackupStatus() {
    try {
      const data = await api("/api/backup/status");
      const job = data.job;
      if (job && job.running) {
        state.backupJob = job;
        updateBackupUI();
        if (dom.backupDialog.open) renderBackupJob(job);
        pollBackup();
      }
    } catch (err) {
      /* status is optional */
    }
  }

  async function copyZipPath() {
    const job = state.backupJob;
    if (!job || !job.zipPath) return;
    const ok = await copyText(job.zipPath);
    showToast(ok ? "zip 路径已复制" : "复制失败，请手动选择路径", { error: !ok });
  }

  // ---------------------------------------------------------------- canvas

  function resizeCanvas() {
    const rect = dom.stage.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    const nextDpr = Math.min(2, window.devicePixelRatio || 1);
    if (width === cssW && height === cssH && nextDpr === dpr) return;
    hideSelectionMenu();
    cssW = width;
    cssH = height;
    dpr = nextDpr;
    dom.canvas.width = Math.round(cssW * dpr);
    dom.canvas.height = Math.round(cssH * dpr);
    if (state.info && state.autoFit) {
      fitView();
    } else if (state.info && state.hasView) {
      clampCamera();
      updateHud();
      requestDraw();
    } else {
      requestDraw();
    }
  }

  function screenToWorld(px, py) {
    return {
      x: state.camera.cx + (px - cssW / 2) / state.camera.scale,
      z: state.camera.cz + (py - cssH / 2) / state.camera.scale,
    };
  }

  function worldToScreenX(wx) {
    return (wx - state.camera.cx) * state.camera.scale + cssW / 2;
  }

  function worldToScreenZ(wz) {
    return (wz - state.camera.cz) * state.camera.scale + cssH / 2;
  }

  function requestDraw() {
    if (state.raf) return;
    state.raf = requestAnimationFrame(() => {
      state.raf = 0;
      draw();
    });
  }

  function draw() {
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const bg = ctx.createRadialGradient(
      cssW * 0.62,
      cssH * 0.32,
      30,
      cssW * 0.62,
      cssH * 0.32,
      Math.max(cssW, cssH) * 0.85
    );
    bg.addColorStop(0, "#0d131b");
    bg.addColorStop(1, "#070a0e");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, cssW, cssH);

    const dim = currentDim();
    if (!dim) {
      updateRenderBadge();
      return;
    }

    const s = state.camera.scale;
    const rpx = REGION * s;
    const viewLeft = state.camera.cx - cssW / (2 * s);
    const viewRight = state.camera.cx + cssW / (2 * s);
    const viewTop = state.camera.cz - cssH / (2 * s);
    const viewBottom = state.camera.cz + cssH / (2 * s);
    const b = contentBounds(dim);
    const rx0 = Math.max(Math.floor(viewLeft / REGION), b.x1);
    const rx1 = Math.min(Math.floor(viewRight / REGION), b.x2);
    const rz0 = Math.max(Math.floor(viewTop / REGION), b.z1);
    const rz1 = Math.min(Math.floor(viewBottom / REGION), b.z2);
    const regionMap = dim._regions;
    const prefer = s >= 0.6 ? 512 : 256;

    if (rx1 >= rx0 && rz1 >= rz0) {
      const cellCount = (rx1 - rx0 + 1) * (rz1 - rz0 + 1);
      if (cellCount <= 3500) {
        for (let rx = rx0; rx <= rx1; rx += 1) {
          for (let rz = rz0; rz <= rz1; rz += 1) {
            const x = worldToScreenX(rx * REGION);
            const y = worldToScreenZ(rz * REGION);
            const known = regionMap.has(rx + "," + rz);
            drawRegionCell(dim.id, rx, rz, x, y, rpx, prefer, known, s);
          }
        }
        drawRegionGrid(rx0, rx1, rz0, rz1, b);
        if (selectionUnit() === CHUNK) {
          drawChunkGrid(dim, viewLeft, viewRight, viewTop, viewBottom);
        }
        drawRegionLabels(dim, rx0, rx1, rz0, rz1, rpx);
      } else {
        for (const region of dim.regions) {
          if (region.x < rx0 || region.x > rx1 || region.z < rz0 || region.z > rz1) continue;
          const x = worldToScreenX(region.x * REGION);
          const y = worldToScreenZ(region.z * REGION);
          drawRegionCell(dim.id, region.x, region.z, x, y, rpx, prefer, true, s);
        }
      }
    }

    drawHoverCell(dim);
    drawSelections();
    drawWaypoints();
    drawDragPreview();
    updateRenderBadge();
  }

  function drawRegionCell(dimId, rx, rz, x, y, size, prefer, known, scale) {
    if (!known) {
      ctx.fillStyle = "rgba(255,255,255,0.014)";
      ctx.fillRect(x, y, size, size);
      if (size >= 34) {
        ctx.fillStyle = "rgba(255,255,255,0.055)";
        ctx.beginPath();
        ctx.arc(x + size / 2, y + size / 2, Math.min(1.8, size * 0.035), 0, Math.PI * 2);
        ctx.fill();
      }
      return;
    }
    if (size < 6) {
      ctx.fillStyle = "rgba(74,222,159,0.2)";
      ctx.fillRect(x, y, size, size);
      return;
    }
    const tile = ensureTile(dimId, rx, rz, prefer);
    let img = tile.img;
    if (!img) {
      const alt = state.tiles.get(tileKey(dimId, rx, rz, prefer === 512 ? 256 : 512));
      if (alt && alt.img) img = alt.img;
    }
    if (img) {
      const smooth = scale < 1.6;
      ctx.imageSmoothingEnabled = smooth;
      if (smooth) ctx.imageSmoothingQuality = "high";
      ctx.drawImage(img, x, y, size + 0.75, size + 0.75);
    } else {
      ctx.fillStyle = "rgba(28,38,52,0.65)";
      ctx.fillRect(x, y, size, size);
      if (size >= 30) {
        ctx.fillStyle = "rgba(255,255,255,0.08)";
        ctx.beginPath();
        ctx.arc(x + size / 2, y + size / 2, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function drawRegionGrid(rx0, rx1, rz0, rz1, b) {
    const left = worldToScreenX(rx0 * REGION);
    const top = worldToScreenZ(rz0 * REGION);
    const right = worldToScreenX((rx1 + 1) * REGION);
    const bottom = worldToScreenZ((rz1 + 1) * REGION);
    ctx.strokeStyle = "rgba(255,255,255,0.055)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let rx = rx0; rx <= rx1 + 1; rx += 1) {
      const x = Math.round(worldToScreenX(rx * REGION)) + 0.5;
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
    }
    for (let rz = rz0; rz <= rz1 + 1; rz += 1) {
      const y = Math.round(worldToScreenZ(rz * REGION)) + 0.5;
      ctx.moveTo(left, y);
      ctx.lineTo(right, y);
    }
    ctx.stroke();

    const bLeft = Math.round(worldToScreenX(b.x1 * REGION)) + 0.5;
    const bTop = Math.round(worldToScreenZ(b.z1 * REGION)) + 0.5;
    const bRight = Math.round(worldToScreenX((b.x2 + 1) * REGION)) + 0.5;
    const bBottom = Math.round(worldToScreenZ((b.z2 + 1) * REGION)) + 0.5;
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.strokeRect(bLeft, bTop, bRight - bLeft, bBottom - bTop);
  }

  function drawChunkGrid(dim, viewLeft, viewRight, viewTop, viewBottom) {
    const s = state.camera.scale;
    const cell = CHUNK * s;
    if (cell < 8) return;
    const b = contentBounds(dim);
    const left = Math.max(viewLeft, b.x1 * REGION);
    const right = Math.min(viewRight, (b.x2 + 1) * REGION);
    const top = Math.max(viewTop, b.z1 * REGION);
    const bottom = Math.min(viewBottom, (b.z2 + 1) * REGION);
    if (right <= left || bottom <= top) return;

    const cx0 = Math.floor(left / CHUNK);
    const cx1 = Math.max(cx0, Math.ceil(right / CHUNK) - 1);
    const cz0 = Math.floor(top / CHUNK);
    const cz1 = Math.max(cz0, Math.ceil(bottom / CHUNK) - 1);
    const count = (cx1 - cx0 + 1) * (cz1 - cz0 + 1);

    if (count <= 9000) {
      ctx.beginPath();
      for (let cx = cx0; cx <= cx1; cx += 1) {
        for (let cz = cz0; cz <= cz1; cz += 1) {
          const region = dim._regions.get(
            Math.floor(cx / 32) + "," + Math.floor(cz / 32)
          );
          if (!chunkExistsInRegion(region, cx, cz)) continue;
          const x = worldToScreenX(cx * CHUNK);
          const y = worldToScreenZ(cz * CHUNK);
          ctx.rect(x + cell / 2 - 1, y + cell / 2 - 1, 2, 2);
        }
      }
      ctx.fillStyle = "rgba(164,232,203,0.22)";
      ctx.fill();
    }

    const xStart = Math.round(worldToScreenX(cx0 * CHUNK)) + 0.5;
    const xEnd = Math.round(worldToScreenX((cx1 + 1) * CHUNK)) + 0.5;
    const yStart = Math.round(worldToScreenZ(cz0 * CHUNK)) + 0.5;
    const yEnd = Math.round(worldToScreenZ((cz1 + 1) * CHUNK)) + 0.5;
    ctx.strokeStyle = "rgba(255,255,255,0.045)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let cx = cx0; cx <= cx1 + 1; cx += 1) {
      const x = Math.round(worldToScreenX(cx * CHUNK)) + 0.5;
      ctx.moveTo(x, yStart);
      ctx.lineTo(x, yEnd);
    }
    for (let cz = cz0; cz <= cz1 + 1; cz += 1) {
      const y = Math.round(worldToScreenZ(cz * CHUNK)) + 0.5;
      ctx.moveTo(xStart, y);
      ctx.lineTo(xEnd, y);
    }
    ctx.stroke();
  }

  function drawRegionLabels(dim, rx0, rx1, rz0, rz1, rpx) {
    if (rpx < 62) return;
    const cellCount = (rx1 - rx0 + 1) * (rz1 - rz0 + 1);
    if (cellCount > 260) return;
    ctx.font = '10px ' + FONT_MONO;
    ctx.textBaseline = "top";
    for (let rx = rx0; rx <= rx1; rx += 1) {
      for (let rz = rz0; rz <= rz1; rz += 1) {
        const x = worldToScreenX(rx * REGION);
        const y = worldToScreenZ(rz * REGION);
        if (x + 90 < 0 || x > cssW || y + 26 < 0 || y > cssH) continue;
        const known = dim._regions.has(rx + "," + rz);
        const label = "r." + rx + "." + rz;
        const width = ctx.measureText(label).width;
        const boxX = Math.round(x) + 6;
        const boxY = Math.round(y) + 6;
        ctx.fillStyle = "rgba(6,10,14,0.62)";
        ctx.beginPath();
        if (typeof ctx.roundRect === "function") {
          ctx.roundRect(boxX, boxY, width + 10, 17, 4);
        } else {
          ctx.rect(boxX, boxY, width + 10, 17);
        }
        ctx.fill();
        ctx.fillStyle = known ? "rgba(214,230,246,0.72)" : "rgba(150,162,180,0.42)";
        ctx.fillText(label, boxX + 5, boxY + 4);
      }
    }
  }

  function drawHoverCell(dim) {
    if (!state.hover) return;
    const unit = selectionUnit();
    const ux = Math.floor(state.hover.x / unit) * unit;
    const uz = Math.floor(state.hover.z / unit) * unit;
    const b = contentBounds(dim);
    if (
      ux < b.x1 * REGION ||
      ux >= (b.x2 + 1) * REGION ||
      uz < b.z1 * REGION ||
      uz >= (b.z2 + 1) * REGION
    ) {
      return;
    }
    let known;
    if (unit === CHUNK) {
      const cx = ux / CHUNK;
      const cz = uz / CHUNK;
      const region = dim._regions.get(
        Math.floor(cx / 32) + "," + Math.floor(cz / 32)
      );
      known = chunkExistsInRegion(region, cx, cz);
    } else {
      known = dim._regions.has(Math.floor(ux / REGION) + "," + Math.floor(uz / REGION));
    }
    const x = worldToScreenX(ux);
    const y = worldToScreenZ(uz);
    const size = unit * state.camera.scale;
    if (x + size < 0 || y + size < 0 || x > cssW || y > cssH) return;
    ctx.fillStyle = known ? "rgba(255,255,255,0.035)" : "rgba(248,113,113,0.055)";
    ctx.fillRect(x, y, size, size);
    ctx.strokeStyle = known ? "rgba(255,255,255,0.34)" : "rgba(248,113,113,0.5)";
    ctx.lineWidth = 1.25;
    ctx.strokeRect(x + 1, y + 1, Math.max(1, size - 2), Math.max(1, size - 2));
  }

  const outlineCache = new WeakMap();

  // Multiple rectangles in one selection often share edges. Collecting their
  // edges and cancelling opposite overlaps leaves only the merged outline, so
  // adjacent activity chunks no longer draw doubled internal borders.
  function selectionOutlineSegments(parts) {
    if (!Array.isArray(parts) || parts.length < 2) return { h: [], v: [] };
    const cached = outlineCache.get(parts);
    if (cached) return cached;

    const hLines = new Map();
    const vLines = new Map();
    const addEdge = (map, fixed, start, end, sign) => {
      let list = map.get(fixed);
      if (!list) {
        list = [];
        map.set(fixed, list);
      }
      list.push([start, sign], [end, -sign]);
    };
    for (const part of parts) {
      addEdge(hLines, part.z1, part.x1, part.x2 + 1, 1);
      addEdge(hLines, part.z2 + 1, part.x1, part.x2 + 1, -1);
      addEdge(vLines, part.x1, part.z1, part.z2 + 1, 1);
      addEdge(vLines, part.x2 + 1, part.z1, part.z2 + 1, -1);
    }

    const collect = (lines) => {
      const segments = [];
      for (const [fixed, events] of lines) {
        events.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
        let net = 0;
        let prev = null;
        let segStart = null;
        let segEnd = null;
        let i = 0;
        while (i < events.length) {
          const at = events[i][0];
          if (net !== 0 && prev !== null && at > prev) {
            if (segStart === null) segStart = prev;
            segEnd = at;
          }
          let delta = 0;
          while (i < events.length && events[i][0] === at) {
            delta += events[i][1];
            i += 1;
          }
          net += delta;
          prev = at;
          if (net === 0 && segStart !== null) {
            segments.push([fixed, segStart, segEnd]);
            segStart = null;
            segEnd = null;
          }
        }
        if (segStart !== null) segments.push([fixed, segStart, segEnd]);
      }
      return segments;
    };

    const result = { h: collect(hLines), v: collect(vLines) };
    outlineCache.set(parts, result);
    return result;
  }

  function traceOutlineSegments(outline) {
    ctx.beginPath();
    for (const [z, x0, x1] of outline.h) {
      const y = worldToScreenZ(z);
      if (y < -8 || y > cssH + 8) continue;
      const sx0 = worldToScreenX(x0);
      const sx1 = worldToScreenX(x1);
      if (sx1 < -8 || sx0 > cssW + 8) continue;
      ctx.moveTo(sx0, y);
      ctx.lineTo(sx1, y);
    }
    for (const [x, z0, z1] of outline.v) {
      const sx = worldToScreenX(x);
      if (sx < -8 || sx > cssW + 8) continue;
      const sz0 = worldToScreenZ(z0);
      const sz1 = worldToScreenZ(z1);
      if (sz1 < -8 || sz0 > cssH + 8) continue;
      ctx.moveTo(sx, sz0);
      ctx.lineTo(sx, sz1);
    }
  }

  function drawSelections() {
    const sels = currentSelections();
    // Activity is drawn first so it stays at the bottom and regular
    // selections remain visible above it.
    sels.forEach((sel) => {
      if (sel.special === "activity") drawSelection(sel, 0, ACTIVITY_COLOR);
    });
    let number = 0;
    sels.forEach((sel, index) => {
      if (sel.special === "activity") return;
      number += 1;
      drawSelection(sel, number, SELECTION_COLORS[index % SELECTION_COLORS.length]);
    });
  }

  function drawSelection(sel, number, color) {
    const parts = getParts(sel);
    const active = state.activeSelId === sel.id;
    const compact = state.camera.scale < CHUNK_ZOOM;
    const special = sel.special === "activity";
    // At region zoom the activity outline turns into a heavy frame around
    // very thin chunk fills; drop it and lean on a denser fill instead.
    const hideOutline = special && compact;
    // A scan can produce thousands of rectangles; batching them into one
    // path and skipping per-rect decorations keeps panning responsive.
    const dense = parts.length > 500;
    const multi = parts.length > 1;
    const spread = compact ? 2.5 : 1.5;
    const visible = [];
    ctx.beginPath();
    for (const part of parts) {
      const x = worldToScreenX(part.x1);
      const y = worldToScreenZ(part.z1);
      const width = (part.x2 - part.x1 + 1) * state.camera.scale;
      const height = (part.z2 - part.z1 + 1) * state.camera.scale;
      if (x + width + spread < 0 || y + height + spread < 0 || x - spread > cssW || y - spread > cssH) {
        continue;
      }
      if (multi) {
        // Sub-rectangles tile the same selection; draw them without the
        // outward padding so the merged outline can trace exact boundaries.
        ctx.rect(x, y, width, height);
        visible.push({ x, y, width, height });
      } else {
        const rx = x - spread;
        const ry = y - spread;
        const rw = width + spread * 2;
        const rh = height + spread * 2;
        ctx.rect(rx, ry, rw, rh);
        visible.push({ x, y, width, height });
      }
    }
    if (!visible.length) return;

    let fillAlpha;
    if (special && compact) {
      // Ramp from 0.55 at the chunk threshold up to 0.8 at 20% zoom so the
      // activity overlay stays visible without turning into a solid block.
      const t = clamp((CHUNK_ZOOM - state.camera.scale) / (CHUNK_ZOOM - 0.2), 0, 1);
      fillAlpha = 0.55 + (0.8 - 0.55) * t;
      if (active) fillAlpha = Math.min(0.92, fillAlpha + 0.1);
    } else if (active) {
      fillAlpha = 0.3;
    } else {
      fillAlpha = compact ? 0.24 : 0.18;
    }
    ctx.fillStyle = hexA(color, fillAlpha);
    ctx.fill();
    if (multi) {
      if (!hideOutline) {
        const outline = selectionOutlineSegments(parts);
        ctx.save();
        ctx.lineCap = "round";
        ctx.strokeStyle = hexA(color, active ? 1 : 0.95);
        ctx.lineWidth = (active ? 2.4 : compact ? 2 : 1.6) + (compact ? 3.5 : 1.5);
        traceOutlineSegments(outline);
        ctx.stroke();
        ctx.restore();
      }
    } else if (!hideOutline) {
      ctx.strokeStyle = hexA(color, active ? 1 : 0.95);
      ctx.lineWidth = active ? 2.4 : compact ? 2 : 1.6;
      ctx.save();
      if (compact && !dense) {
        ctx.shadowColor = hexA(color, 0.45);
        ctx.shadowBlur = 6;
      }
      ctx.stroke();
      ctx.restore();
      if (active && !dense) {
        ctx.save();
        ctx.setLineDash([2, 4]);
        ctx.lineWidth = 1;
        ctx.strokeStyle = "rgba(255,255,255,0.32)";
        for (const rect of visible) {
          if (rect.width < 16 || rect.height < 16) continue;
          ctx.strokeRect(
            rect.x + 4.5,
            rect.y + 4.5,
            Math.max(1, rect.width - 9),
            Math.max(1, rect.height - 9)
          );
        }
        ctx.restore();
      }
    }

    let anchor = visible[0];
    if (visible.length > 1) {
      let bestArea = anchor.width * anchor.height;
      for (let i = 1; i < visible.length; i += 1) {
        const area = visible[i].width * visible[i].height;
        if (area > bestArea) {
          bestArea = area;
          anchor = visible[i];
        }
      }
    }
    if (anchor.width < 58 || anchor.height < 22) return;
    ctx.font = '600 11px ' + FONT_UI;
    ctx.textBaseline = "top";
    const label =
      (special
        ? "活动选区 · " + activityChunkCount(sel) + " 区块"
        : number + ". " + (sel.desc || "选区")) +
      (active ? " · 当前" : "") +
      (!special && parts.length > 1 ? " · " + parts.length + " 个选区" : "");
    const maxText = Math.min(anchor.width - 22, 250);
    const text = truncateText(label, maxText);
    const textWidth = ctx.measureText(text).width;
    const chipWidth = textWidth + 16;
    const chipHeight = 20;
    const chipX = clamp(anchor.x + 6, 4, cssW - chipWidth - 4);
    const chipY = clamp(anchor.y + 6, 4, cssH - chipHeight - 4);
    const radius = 5;
    ctx.fillStyle = "rgba(7,11,16,0.82)";
    ctx.beginPath();
    if (typeof ctx.roundRect === "function") ctx.roundRect(chipX, chipY, chipWidth, chipHeight, radius);
    else ctx.rect(chipX, chipY, chipWidth, chipHeight);
    ctx.fill();
    ctx.strokeStyle = hexA(color, active ? 0.8 : 0.45);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = "#eaf6ff";
    ctx.fillText(text, chipX + 8, chipY + 4);
  }

  function drawWaypoints() {
    if (!state.showWaypoints) return;
    const dim = currentDim();
    const list = dim ? state.waypoints[dim.id] : null;
    if (!Array.isArray(list) || !list.length) return;

    const visible = [];
    for (const wp of list) {
      if (!wp || !Number.isFinite(wp.x) || !Number.isFinite(wp.z)) continue;
      const x = worldToScreenX(wp.x);
      const y = worldToScreenZ(wp.z);
      if (x < -20 || x > cssW + 20 || y < -20 || y > cssH + 20) continue;
      const color = /^#[0-9a-f]{6}$/i.test(wp.color || "") ? wp.color : "#ffffff";
      visible.push({ wp, x, y, color });
    }
    if (!visible.length) return;

    for (const item of visible) drawWaypointMarker(item.x, item.y, item.color);
    if (state.camera.scale < 0.012 && visible.length > 24) return;

    ctx.font = "600 10.5px " + FONT_UI;
    ctx.textBaseline = "middle";
    const placed = [];
    visible.sort((a, b) => a.y - b.y || a.x - b.x);
    for (const item of visible) {
      const text = truncateText(item.wp.name || "路径点", 150);
      const chipWidth = ctx.measureText(text).width + 12;
      const chipHeight = 18;
      const offsets = [
        [9, -chipHeight / 2],
        [9, -chipHeight - 5],
        [9, 8],
        [9, -chipHeight * 2 - 10],
        [9, chipHeight + 11],
        [-chipWidth - 9, -chipHeight / 2],
        [-chipWidth - 9, -chipHeight - 5],
        [-chipWidth - 9, 8],
        [-chipWidth - 9, -chipHeight * 2 - 10],
        [-chipWidth - 9, chipHeight + 11],
        [-chipWidth / 2, -chipHeight - 10],
        [-chipWidth / 2, 11],
      ];
      let box = null;
      let fallback = null;
      let fallbackScore = Infinity;
      for (const [dx, dy] of offsets) {
        const x = clamp(item.x + dx, 4, Math.max(4, cssW - chipWidth - 4));
        const y = clamp(item.y + dy, 4, cssH - chipHeight - 4);
        let score = 0;
        for (const other of placed) {
          const overlapX = Math.max(
            0,
            Math.min(x + chipWidth, other.x + other.width) - Math.max(x, other.x)
          );
          const overlapY = Math.max(
            0,
            Math.min(y + chipHeight, other.y + other.height) - Math.max(y, other.y)
          );
          score += overlapX * overlapY;
        }
        const candidate = { x, y, width: chipWidth, height: chipHeight };
        if (score === 0) {
          box = candidate;
          break;
        }
        if (score < fallbackScore) {
          fallbackScore = score;
          fallback = candidate;
        }
      }
      if (!box) box = fallback;
      if (!box) continue;
      placed.push(box);
      ctx.fillStyle = "rgba(6,10,15,0.8)";
      ctx.beginPath();
      if (typeof ctx.roundRect === "function") ctx.roundRect(box.x, box.y, box.width, box.height, 4);
      else ctx.rect(box.x, box.y, box.width, box.height);
      ctx.fill();
      ctx.strokeStyle = hexA(item.color, 0.55);
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#f0f7ff";
      ctx.fillText(text, box.x + 6, box.y + box.height / 2 + 0.5);
    }
  }

  function drawWaypointMarker(x, y, color) {
    ctx.beginPath();
    ctx.moveTo(x, y - 7);
    ctx.lineTo(x + 6, y);
    ctx.lineTo(x, y + 7);
    ctx.lineTo(x - 6, y);
    ctx.closePath();
    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,0.8)";
    ctx.shadowBlur = 6;
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = "rgba(4,8,13,0.92)";
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, 1.5, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.88)";
    ctx.fill();
  }

  function drawDragPreview() {
    const drag = state.drag;
    if (!drag || drag.type !== "select" || !drag.moved) return;
    const b = computeDragBounds(drag.startWorld, drag.currentWorld);
    const x = worldToScreenX(b.x1);
    const y = worldToScreenZ(b.z1);
    const width = (b.x2 - b.x1 + 1) * state.camera.scale;
    const height = (b.z2 - b.z1 + 1) * state.camera.scale;
    ctx.fillStyle = "rgba(251,191,36,0.12)";
    ctx.fillRect(x, y, width, height);
    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = "rgba(251,191,36,0.95)";
    ctx.strokeRect(x + 0.75, y + 0.75, Math.max(1, width - 1.5), Math.max(1, height - 1.5));
    ctx.restore();
  }

  function truncateText(text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) return text;
    let result = text;
    while (result.length > 1 && ctx.measureText(result + "…").width > maxWidth) {
      result = result.slice(0, -1);
    }
    return result + "…";
  }

  // ---------------------------------------------------------------- tiles

  function tileKey(dimId, rx, rz, res) {
    return dimId + "|" + rx + "|" + rz + "|" + res;
  }

  function ensureTile(dimId, rx, rz, res) {
    const key = tileKey(dimId, rx, rz, res);
    let tile = state.tiles.get(key);
    if (!tile) {
      tile = {
        key,
        dimId,
        rx,
        rz,
        res,
        status: "loading",
        img: null,
        failed: 0,
        token: state.token,
      };
      state.tiles.set(key, tile);
      enqueueTile(tile);
      maybeEvictTiles();
    }
    return tile;
  }

  function enqueueTile(tile) {
    state.tileQueue.push(tile);
    pumpTiles();
  }

  function pumpTiles() {
    const maxActive = 5;
    while (state.activeTiles < maxActive && state.tileQueue.length) {
      const tile = state.tileQueue.shift();
      if (!tile) continue;
      if (tile.token !== state.token) continue;
      if (tile.status !== "loading") continue;
      if (state.tiles.get(tile.key) !== tile) continue;
      state.activeTiles += 1;
      runTile(tile)
        .catch(() => {})
        .finally(() => {
          state.activeTiles -= 1;
          pumpTiles();
        });
    }
  }

  async function runTile(tile) {
    try {
      const url =
        "/api/tile?dim=" +
        encodeURIComponent(tile.dimId) +
        "&x=" +
        tile.rx +
        "&z=" +
        tile.rz +
        "&res=" +
        tile.res;
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const buffer = await res.arrayBuffer();
      if (buffer.byteLength !== tile.res * tile.res * 4) throw new Error("瓦片尺寸不匹配");
      const pixels = new Uint8ClampedArray(buffer);
      const bitmap = await createImageBitmap(new ImageData(pixels, tile.res, tile.res));
      if (tile.token !== state.token) {
        if (bitmap.close) bitmap.close();
        return;
      }
      if (tile.img && tile.img.close) tile.img.close();
      tile.img = bitmap;
      tile.status = "ready";
    } catch (err) {
      if (tile.token !== state.token) return;
      if (tile.failed < 2) {
        tile.failed += 1;
        tile.status = "loading";
        window.setTimeout(() => {
          if (tile.token === state.token && state.tiles.get(tile.key) === tile && tile.status === "loading") {
            enqueueTile(tile);
            updateRenderBadge();
          }
        }, 550 * tile.failed);
      } else {
        tile.status = "error";
        tile.error = err.message;
      }
    }
    requestDraw();
    updateRenderBadge();
  }

  function maybeEvictTiles() {
    if (state.tiles.size <= 380) return;
    for (const [key, tile] of state.tiles) {
      if (state.tiles.size <= 300) break;
      if (tile.status === "loading") continue;
      if (tile.img && tile.img.close) tile.img.close();
      state.tiles.delete(key);
    }
  }

  function clearTiles() {
    for (const tile of state.tiles.values()) {
      if (tile.img && tile.img.close) tile.img.close();
    }
    state.tiles.clear();
    state.tileQueue.length = 0;
  }

  function updateRenderBadge() {
    const dim = currentDim();
    dom.renderBadge.classList.remove("error");
    dom.renderBadge.onclick = null;
    if (!dim) {
      dom.renderBadge.hidden = true;
      return;
    }
    const loading = new Set();
    const errors = new Set();
    for (const tile of state.tiles.values()) {
      if (tile.dimId !== dim.id) continue;
      const pos = tile.rx + "," + tile.rz;
      if (tile.status === "loading") loading.add(pos);
      else if (tile.status === "error") errors.add(pos);
    }
    if (loading.size) {
      dom.renderBadge.hidden = false;
      dom.renderText.textContent = "正在渲染 " + loading.size + " 个区域…";
      return;
    }
    if (errors.size) {
      dom.renderBadge.hidden = false;
      dom.renderBadge.classList.add("error");
      dom.renderText.textContent = errors.size + " 个区域读取失败，点击重试";
      dom.renderBadge.onclick = retryFailedTiles;
      return;
    }
    dom.renderBadge.hidden = true;
  }

  function retryFailedTiles() {
    if (!state.dim) return;
    let count = 0;
    for (const tile of state.tiles.values()) {
      if (tile.dimId !== state.dim || tile.status !== "error") continue;
      tile.status = "loading";
      tile.failed = 0;
      enqueueTile(tile);
      count += 1;
    }
    if (count) {
      showToast("正在重试 " + count + " 个区域");
      requestDraw();
      updateRenderBadge();
    }
  }

  // ---------------------------------------------------------------- interaction

  function setMode(mode) {
    state.mode = mode;
    dom.modeSelect.classList.toggle("active", mode === "select");
    dom.modePan.classList.toggle("active", mode === "pan");
    updateCanvasCursor();
    saveSettings();
  }

  function updateCanvasCursor() {
    const pan = state.mode === "pan" || state.space;
    dom.canvas.classList.toggle("select-mode", !pan);
    dom.canvas.classList.toggle("pan-mode", pan);
    dom.canvas.classList.toggle("grabbing", !!state.drag && state.drag.type === "pan");
  }

  function zoomBy(factor) {
    if (!state.info) return;
    const px = cssW / 2;
    const py = cssH / 2;
    const before = screenToWorld(px, py);
    const nextScale = clamp(state.camera.scale * factor, minZoomScale(), MAX_SCALE);
    state.camera.scale = nextScale;
    state.camera.cx = before.x - (px - cssW / 2) / nextScale;
    state.camera.cz = before.z - (py - cssH / 2) / nextScale;
    state.autoFit = false;
    clampCamera();
    updateHoverFromScreen(px, py);
    hideActivityTip();
    updateHud();
    requestDraw();
  }

  function onWheel(event) {
    if (!state.info || !currentDim()) return;
    hideSelectionMenu();
    event.preventDefault();
    const rect = dom.canvas.getBoundingClientRect();
    const px = clamp(event.clientX - rect.left, 0, cssW);
    const py = clamp(event.clientY - rect.top, 0, cssH);
    const before = screenToWorld(px, py);
    const factor = Math.exp(-event.deltaY * 0.0025);
    const nextScale = clamp(state.camera.scale * factor, minZoomScale(), MAX_SCALE);
    if (nextScale === state.camera.scale) return;
    state.camera.scale = nextScale;
    state.camera.cx = before.x - (px - cssW / 2) / nextScale;
    state.camera.cz = before.z - (py - cssH / 2) / nextScale;
    state.autoFit = false;
    clampCamera();
    updateHoverFromScreen(px, py);
    updateActivityHoverTip(event, state.hover);
    updateHud();
    requestDraw();
  }

  function updateHoverFromScreen(px, py) {
    if (!state.info || !currentDim()) {
      state.hover = null;
      return;
    }
    const world = screenToWorld(px, py);
    state.hover = { x: world.x, z: world.z };
  }

  function onPointerDown(event) {
    if (!currentDim()) return;
    if (event.button !== 0 && event.button !== 1) return;
    hideSelectionMenu();
    hideActivityTip();
    const rect = dom.canvas.getBoundingClientRect();
    const px = clamp(event.clientX - rect.left, 0, cssW);
    const py = clamp(event.clientY - rect.top, 0, cssH);
    const pan = event.button === 1 || state.mode === "pan" || state.space;
    try {
      dom.canvas.setPointerCapture(event.pointerId);
    } catch (err) {
      /* pointer capture is best-effort */
    }
    if (pan) {
      event.preventDefault();
      state.drag = {
        type: "pan",
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        cam: { ...state.camera },
      };
    } else {
      const world = screenToWorld(px, py);
      const additive = event.ctrlKey || event.metaKey;
      const hit = hitSelection(world);
      state.drag = {
        type: "select",
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startWorld: world,
        currentWorld: world,
        moved: false,
        hitId: hit ? hit.id : "",
        additive,
        targetId: additive ? (hit ? hit.id : "") || state.activeSelId : "",
      };
    }
    updateHoverFromScreen(px, py);
    updateHud();
    updateCanvasCursor();
  }

  function onPointerMove(event) {
    if (!state.info) return;
    const rect = dom.canvas.getBoundingClientRect();
    const px = clamp(event.clientX - rect.left, 0, cssW);
    const py = clamp(event.clientY - rect.top, 0, cssH);
    updateHoverFromScreen(px, py);

    const drag = state.drag;
    if (drag && event.pointerId === drag.pointerId) {
      hideActivityTip();
      if (drag.type === "pan") {
        const dx = event.clientX - drag.startX;
        const dy = event.clientY - drag.startY;
        state.autoFit = false;
        state.camera.cx = drag.cam.cx - dx / state.camera.scale;
        state.camera.cz = drag.cam.cz - dy / state.camera.scale;
        clampCamera();
        updateHoverFromScreen(px, py);
        updateHud();
        requestDraw();
      } else {
        drag.currentWorld = screenToWorld(px, py);
        if (Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 4) {
          drag.moved = true;
        }
        if (drag.moved) {
          updateDragTip(event, computeDragBounds(drag.startWorld, drag.currentWorld));
          requestDraw();
        }
        updateHud();
      }
      return;
    }

    if (state.hover) {
      const unit = selectionUnit();
      const key =
        Math.floor(state.hover.x / unit) + "," + Math.floor(state.hover.z / unit);
      if (key !== state.hoverKey) {
        state.hoverKey = key;
        requestDraw();
      }
    }
    updateActivityHoverTip(event, state.hover);
    updateHud();
  }

  function onPointerUp(event) {
    finishDrag(event, false);
  }

  function onPointerCancel(event) {
    finishDrag(event, true);
  }

  function finishDrag(event, cancelled) {
    const drag = state.drag;
    if (!drag) return;
    if (event && event.pointerId !== undefined && event.pointerId !== drag.pointerId) return;
    state.drag = null;
    dom.dragTip.hidden = true;
    hideActivityTip();
    updateCanvasCursor();
    if (!cancelled) {
      if (drag.type === "select") {
        if (drag.moved) {
          const bounds = computeDragBounds(drag.startWorld, drag.currentWorld);
          if (drag.additive && drag.targetId) addPartToSelection(drag.targetId, bounds);
          else commitSelectionDrag(bounds);
        } else if (drag.hitId) {
          setActiveSelection(drag.hitId, true);
        }
      }
    }
    if (event && event.pointerId !== undefined) {
      try {
        dom.canvas.releasePointerCapture(event.pointerId);
      } catch (err) {
        /* ignore */
      }
    }
    requestDraw();
    updateHud();
  }

  function cancelDrag() {
    if (!state.drag) return;
    state.drag = null;
    dom.dragTip.hidden = true;
    updateCanvasCursor();
    requestDraw();
  }

  function onPointerLeave() {
    if (state.drag) return;
    state.hover = null;
    state.hoverKey = "";
    hideActivityTip();
    updateHud();
    requestDraw();
  }

  function chunkCountOfBounds(bounds) {
    return (
      (Math.floor(bounds.x2 / CHUNK) - Math.floor(bounds.x1 / CHUNK) + 1) *
      (Math.floor(bounds.z2 / CHUNK) - Math.floor(bounds.z1 / CHUNK) + 1)
    );
  }

  function computeDragBounds(a, b2) {
    const minX = Math.floor(Math.min(a.x, b2.x));
    const maxX = Math.floor(Math.max(a.x, b2.x));
    const minZ = Math.floor(Math.min(a.z, b2.z));
    const maxZ = Math.floor(Math.max(a.z, b2.z));
    if (!state.snap) {
      return { x1: minX, z1: minZ, x2: maxX, z2: maxZ };
    }
    const unit = selectionUnit();
    const ux0 = Math.floor(minX / unit);
    const ux1 = Math.floor(maxX / unit);
    const uz0 = Math.floor(minZ / unit);
    const uz1 = Math.floor(maxZ / unit);
    return {
      x1: ux0 * unit,
      z1: uz0 * unit,
      x2: (ux1 + 1) * unit - 1,
      z2: (uz1 + 1) * unit - 1,
    };
  }

  function placeFloatingTip(node, event) {
    const rect = dom.stage.getBoundingClientRect();
    const left = event.clientX - rect.left;
    const top = event.clientY - rect.top;
    node.style.left = left + "px";
    node.style.top = top + "px";
    node.classList.toggle("flip-x", left + 14 + node.offsetWidth > rect.width);
    node.classList.toggle("flip-y", top + 14 + node.offsetHeight > rect.height);
  }

  function hideActivityTip() {
    if (!dom.activityTip.hidden) dom.activityTip.hidden = true;
  }

  function updateActivityHoverTip(event, world) {
    if (!state.info || !world) {
      hideActivityTip();
      return;
    }
    const sel = findActivitySelectionAt(world);
    if (!sel) {
      hideActivityTip();
      return;
    }
    const cx = Math.floor(world.x / CHUNK);
    const cz = Math.floor(world.z / CHUNK);
    const ticks = activityChunkTime(sel, cx, cz);
    const lines = ["区块 " + cx + ", " + cz];
    if (ticks === null) lines.push("活动时长数据缺失，重新扫描可更新");
    else lines.push("活动时长 " + formatActivityTicks(ticks));
    dom.activityTip.textContent = lines.join("\n");
    dom.activityTip.hidden = false;
    placeFloatingTip(dom.activityTip, event);
  }

  function updateDragTip(event, bounds) {
    const width = bounds.x2 - bounds.x1 + 1;
    const height = bounds.z2 - bounds.z1 + 1;
    const unit = selectionUnit();
    const active = findActiveSelection();
    let countText;
    if (state.snap && unit === CHUNK) {
      countText = chunkCountOfBounds(bounds) + " 个区块";
    } else if (state.snap) {
      countText = regionCount(bounds) + " 个区域";
    } else {
      countText = chunkCountOfBounds(bounds) + " 个区块（按区块备份）";
    }
    dom.dragTip.textContent =
      "X " +
      bounds.x1 +
      " … " +
      bounds.x2 +
      "\nZ " +
      bounds.z1 +
      " … " +
      bounds.z2 +
      "\n" +
      width +
      " × " +
      height +
      " 方块 · " +
      countText +
      "\n" +
      (active ? "追加到「" + active.desc + "」" : "松开后新建选区");
    dom.dragTip.hidden = false;
    const rect = dom.stage.getBoundingClientRect();
    const left = event.clientX - rect.left;
    const top = event.clientY - rect.top;
    dom.dragTip.style.left = left + "px";
    dom.dragTip.style.top = top + "px";
    const widthPx = dom.dragTip.offsetWidth;
    const heightPx = dom.dragTip.offsetHeight;
    dom.dragTip.classList.toggle("flip-x", left + 14 + widthPx > rect.width);
    dom.dragTip.classList.toggle("flip-y", top + 14 + heightPx > rect.height);
  }

  function updateHud() {
    const dim = currentDim();
    const unit = selectionUnit();
    dom.hudDim.textContent = dim ? dim.label : "—";
    dom.snapLabel.textContent = state.snap ? "对齐" + unitLabel(unit) : "自由选区";
    dom.snapToggle.parentElement.title =
      "放大到 " + Math.round(CHUNK_ZOOM * 100) + "% 以上按 16×16 区块框选，缩小时按 512×512 区域框选";
    dom.zoomLabel.title = "当前按" + unitLabel(unit) + "框选";
    if (dim && state.hover) {
      const bx = Math.floor(state.hover.x);
      const bz = Math.floor(state.hover.z);
      const rx = Math.floor(bx / REGION);
      const rz = Math.floor(bz / REGION);
      dom.hudCoord.textContent = "X " + bx + " · Z " + bz;
      dom.hudRegion.title = "r." + rx + "." + rz;
      if (unit === CHUNK) {
        const cx = Math.floor(bx / CHUNK);
        const cz = Math.floor(bz / CHUNK);
        const region = dim._regions && dim._regions.get(rx + "," + rz);
        const known = chunkExistsInRegion(region, cx, cz);
        dom.hudRegion.textContent = "区块 " + cx + "," + cz + (known ? "" : " · 未生成");
        dom.hudRegion.classList.toggle("missing", !known);
      } else {
        const known = dim._regions && dim._regions.has(rx + "," + rz);
        dom.hudRegion.textContent = "r." + rx + "." + rz + (known ? "" : " · 未生成");
        dom.hudRegion.classList.toggle("missing", !known);
      }
    } else {
      dom.hudCoord.textContent = "X — · Z —";
      dom.hudRegion.textContent = dim
        ? dim.regionCount + " 区域 · " + (dim.chunkCount || 0) + " 区块"
        : "r.—.—";
      dom.hudRegion.title = "";
      dom.hudRegion.classList.remove("missing");
    }
    const zoomPct = state.camera.scale * 100;
    dom.zoomLabel.textContent =
      (zoomPct >= 10
        ? String(Math.round(zoomPct))
        : zoomPct >= 1
          ? zoomPct.toFixed(1)
          : zoomPct.toFixed(2)) + "%";
  }

  function onKeyDown(event) {
    const target = event.target;
    const tag = target && target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (target && target.isContentEditable)) {
      return;
    }
    // Focus stays on a button after clicking one; keep Space native there so
    // buttons still activate, but let the map shortcuts work.
    if ((tag === "BUTTON" || tag === "A") && event.code === "Space") return;
    if (event.code === "Space") {
      event.preventDefault();
      if (!state.space) {
        state.space = true;
        updateCanvasCursor();
      }
      return;
    }
    if (event.key === "f" || event.key === "F") {
      fitView();
      return;
    }
    if (event.key === "v" || event.key === "V") {
      setMode("select");
      return;
    }
    if (event.key === "h" || event.key === "H") {
      setMode("pan");
      return;
    }
    if (event.key === "n" || event.key === "N") {
      startNewSelection();
      return;
    }
    if (event.key === "Escape") {
      hideSelectionMenu();
      cancelDrag();
      if (state.activeSelId) {
        state.activeSelId = "";
        updateActiveUI();
        renderSelections();
        requestDraw();
        showToast("已结束当前选区");
      }
      return;
    }
    if (event.key === "+" || event.key === "=") {
      zoomBy(1.25);
      return;
    }
    if (event.key === "-" || event.key === "_") {
      zoomBy(0.8);
    }
  }

  function onKeyUp(event) {
    if (event.code === "Space") {
      state.space = false;
      updateCanvasCursor();
    }
  }

  // ---------------------------------------------------------------- toast

  function showToast(message, options) {
    const opts = options || {};
    dom.toastText.textContent = message;
    dom.toast.classList.toggle("error", !!opts.error);
    const hasAction = typeof opts.onAction === "function" && !!opts.action;
    dom.toastAction.hidden = !hasAction;
    if (hasAction) {
      dom.toastAction.textContent = opts.action;
      dom.toastAction._action = opts.onAction;
    } else {
      dom.toastAction._action = null;
    }
    dom.toast.hidden = false;
    clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(hideToast, opts.duration || (hasAction ? 6000 : 2800));
  }

  function hideToast() {
    dom.toast.hidden = true;
    clearTimeout(state.toastTimer);
    state.toastTimer = null;
    dom.toastAction._action = null;
  }

  init();
})();
