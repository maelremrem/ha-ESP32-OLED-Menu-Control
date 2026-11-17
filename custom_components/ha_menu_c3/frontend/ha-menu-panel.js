/* HA Menu C3 — dependency-free Home Assistant custom panel. */
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));
const clone = (obj) => JSON.parse(JSON.stringify(obj));
const rgbHex = (rgb) => "#" + rgb.map((n) => n.toString(16).padStart(2, "0")).join("");
const hexRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

const STYLES = `
  :host { display:block; min-height:100%; color:var(--primary-text-color); background:var(--primary-background-color); font:14px/1.45 var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
  * { box-sizing:border-box; }
  .wrap { max-width:1240px; padding:22px; margin:0 auto; }
  .top { display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:14px; margin-bottom:20px; }
  h1 { font-size:26px; font-weight:650; margin:0; letter-spacing:-.5px; }
  h2 { font-size:18px; font-weight:600; margin:0 0 14px; }
  p { margin:4px 0 0; }
  .sub,.hint { color:var(--secondary-text-color); font-size:13px; }
  .actions { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; background:var(--card-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); border-radius:9px; cursor:pointer; padding:9px 12px; font:inherit; min-height:38px; }
  .btn:hover { background:var(--secondary-background-color); }
  .btn:disabled { opacity:.45; cursor:not-allowed; }
  .primary { background:var(--primary-color); color:var(--text-primary-color,white); border-color:var(--primary-color); }
  .primary:hover { filter:brightness(.95); background:var(--primary-color); }
  .danger { color:var(--error-color,#db4437); }
  .columns { display:grid; grid-template-columns:minmax(295px,420px) minmax(340px,1fr); gap:16px; align-items:start; }
  .panel { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:14px; padding:18px; min-width:0; }
  .panel-head { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:14px; }
  .panel-head h2 { margin:0; }
  .tree { display:flex; flex-direction:column; gap:5px; min-height:120px; }
  .tree-row { display:flex; align-items:center; min-height:43px; border:1px solid transparent; border-radius:9px; cursor:pointer; gap:8px; padding:8px 9px; }
  .tree-row:hover { background:var(--secondary-background-color); }
  .tree-row.active { background:color-mix(in srgb,var(--primary-color) 12%,transparent); border-color:color-mix(in srgb,var(--primary-color) 40%,transparent); }
  .tree-handle { cursor:grab; font-size:17px; color:var(--secondary-text-color); padding:3px; user-select:none; }
  .tree-row.dragging { opacity:.4; }
  .tree-nest { display:flex; align-items:center; gap:3px; flex-shrink:0; }
  .tree-nest button { padding:2px 5px; min-width:25px; min-height:28px; border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color); border-radius:5px; cursor:pointer; font:inherit; }
  .tree-nest button:disabled { opacity:.25; cursor:not-allowed; }
  .tree-nest button:not(:disabled):hover { background:var(--secondary-background-color); }
  .tree-row.drop-before { border-top:3px solid var(--primary-color); }
  .tree-row.drop-after { border-bottom:3px solid var(--primary-color); }
  .tree-row.drop-inside { border:2px dashed var(--primary-color); background:color-mix(in srgb,var(--primary-color) 14%,transparent); }
  .tree-root-drop { border:1px dashed var(--divider-color); border-radius:9px; text-align:center; padding:10px; color:var(--secondary-text-color); margin-top:8px; font-size:12px; }
  .tree-root-drop.drop-inside { border-color:var(--primary-color); background:var(--secondary-background-color); }
  .tree-system { display:flex; border:1px solid var(--divider-color); border-radius:9px; padding:9px 12px; margin-top:7px; color:var(--secondary-text-color); align-items:center; gap:10px; font-size:12px; }
  .tree-item { flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .tree-item small { display:block; font-size:11px; color:var(--secondary-text-color); overflow:hidden; text-overflow:ellipsis; }
  .tree-glyph { width:22px; text-align:center; opacity:.7; }
  .pill { font-size:11px; border:1px solid var(--divider-color); border-radius:30px; padding:3px 9px; }
  .pill.ok { color:var(--success-color,#44a047); }
  .pill.error { color:var(--error-color,#d14536); }
  .notice { margin:0 0 16px; border-radius:8px; padding:10px 12px; background:var(--secondary-background-color); font-size:13px; }
  .notice.error { color:var(--error-color,#d14536); }
  .notice.success { color:var(--success-color,#44a047); }
  .field { display:grid; gap:6px; margin-bottom:15px; }
  .field label { font-size:13px; font-weight:600; }
  input,select,textarea { width:100%; background:var(--primary-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); border-radius:8px; padding:10px 11px; font:inherit; }
  input:focus,select:focus,textarea:focus { outline:2px solid var(--primary-color); outline-offset:-1px; }
  textarea { min-height:100px; resize:vertical; font-family:ui-monospace, SFMono-Regular,Consolas,monospace; font-size:12px; }
  .form-grid { display:grid; grid-template-columns:1fr 1fr; gap:0 12px; }
  .section { border-top:1px solid var(--divider-color); padding-top:17px; margin-top:14px; }
  .small-actions { display:flex; gap:8px; flex-wrap:wrap; margin:12px 0 0; }
  .empty { padding:22px 8px; color:var(--secondary-text-color); text-align:center; }
  .accent { color:var(--primary-color); }
  .led-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .led-grid input[type=color] { height:42px; cursor:pointer; padding:4px; }
  .kbd { padding:2px 5px; border:1px solid var(--divider-color); border-radius:4px; font-size:11px; }
  .meta { margin-top:12px; border-top:1px solid var(--divider-color); padding-top:12px; }
  .tabs { display:flex; gap:8px; border-bottom:1px solid var(--divider-color); margin:0 0 16px; padding-bottom:8px; }
  .tab.active { border-color:var(--primary-color); color:var(--primary-color); font-weight:600; }
  .entity-results { max-height:230px; overflow-y:auto; border:1px solid var(--divider-color); border-radius:8px; margin-top:5px; }
  .entity-option { width:100%; display:flex; align-items:center; gap:9px; text-align:left; border:0; border-bottom:1px solid var(--divider-color); padding:8px 10px; background:var(--card-background-color); color:var(--primary-text-color); cursor:pointer; font:inherit; }
  .entity-option:hover,.entity-option:focus { background:var(--secondary-background-color); }
  .entity-option:last-child { border-bottom:0; }
  .entity-option span { min-width:0; overflow:hidden; text-overflow:ellipsis; }
  .entity-option small { display:block; color:var(--secondary-text-color); font-size:11px; }
  .diagnostics { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; }
  .diagnostic { border:1px solid var(--divider-color); border-radius:10px; padding:12px; min-width:0; }
  .diagnostic strong { display:block; margin-top:3px; overflow-wrap:anywhere; }
  .device-picker { display:flex; gap:7px; align-items:center; min-width:230px; font-size:13px; }
  .device-picker select { min-width:180px; max-width:300px; background:var(--card-background-color); }
  .diagnostic small { display:block; margin-top:5px; font-size:11px; color:var(--secondary-text-color); overflow-wrap:anywhere; }
  .diagnostic.missing { opacity:.75; }
  .control-list { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px; }
  .control-check { display:flex; align-items:center; gap:8px; padding:9px; border:1px solid var(--divider-color); border-radius:8px; cursor:pointer; }
  .control-check input { width:auto; margin:0; }
  .control-check.unsupported { opacity:.55; cursor:not-allowed; }

  @media(max-width:790px) { .wrap{padding:12px;} .columns{grid-template-columns:1fr;} h1{font-size:23px;} .form-grid{grid-template-columns:1fr;} }
`;

class HAMenuC3Panel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this.shadowRoot.addEventListener("click", (event) => this.onClick(event));
    this.shadowRoot.addEventListener("input", (event) => this.onInput(event));
    this.shadowRoot.addEventListener("change", (event) => this.onChange(event));
    this.status = null;
    this.deviceId = null;
    this.devices = [];
    this.savedConfig = null;
    this.selectedId = null;
    this.activeTab = "menus";
    this.notice = "";
    this.noticeType = "";
    this.busy = false;
    this.hasLoaded = false;
    this._hass = null;
    this.editJson = "{}";
    this.editJsonError = "";
    this.dragId = null;
    this.dropTarget = null;
    this.shadowRoot.addEventListener("dragstart", (event) => this.onDragStart(event));
    this.shadowRoot.addEventListener("dragover", (event) => this.onDragOver(event));
    this.shadowRoot.addEventListener("drop", (event) => this.onDrop(event));
    this.shadowRoot.addEventListener("dragend", () => this.clearDrag());
  }

  controlCapabilities(hass, entityId) {
    const state = entityId ? hass?.states?.[entityId] : undefined;
    if (!state) return "missing";
    const attrs = state.attributes || {};
    return JSON.stringify([
      state.state === "unavailable" ? "unavailable" : "available",
      attrs.supported_color_modes || [],
      attrs.supported_features || 0,
      attrs.hvac_modes || [],
      attrs.available_modes || [],
    ]);
  }

  set hass(value) {
    const entityId = this.selected?.entity_id;
    const previous = this.controlCapabilities(this._hass, entityId);
    this._hass = value;
    if (this.isConnected && !this.hasLoaded) this.fetch();
    else if (this.isConnected && this.hasLoaded && entityId &&
             previous !== this.controlCapabilities(value, entityId)) {
      this.refreshControlOptions();
    }
  }
  get hass() { return this._hass; }

  connectedCallback() {
    this.render();
    if (this._hass && !this.hasLoaded) this.fetch();
    this._refreshTimer = setInterval(() => {
      if (this.isConnected && this.activeTab === "config" && this.status && !this.busy) this.refresh();
    }, 15000);
  }

  disconnectedCallback() {
    clearInterval(this._refreshTimer);
  }

  async call(type, extra={}) {
    const message = {type, ...extra};
    if (typeof this._hass?.callWS === "function") return this._hass.callWS(message);
    const response = await this._hass.connection.sendMessagePromise(message);
    return response?.result ?? response;
  }

  show(message, type="") {
    this.notice = message;
    this.noticeType = type;
    this.renderNotice();
  }

  async fetch(deviceId=this.deviceId) {
    if (!this._hass) return;
    this.busy = true;
    try {
      const status = await this.call("ha_menu_c3/get", deviceId ? {entry_id:deviceId} : {});
      this.status = status;
      this.status.config = clone(status.config);
      this.deviceId = status.entry_id;
      this.devices = status.devices || [];
      this.savedConfig = JSON.stringify(status.config);
      this.selectedId = null;
      this.notice = "";
      this.hasLoaded = true;
      this.render();
    } catch (err) {
      if (!this.status) this.hasLoaded = false;
      this.show(`Chargement impossible : ${err.message || err}`, "error");
    } finally { this.busy = false; }
  }

  async selectDevice(nextId) {
    if (!nextId || nextId === this.deviceId || this.busy) return;
    if (!this.commitEditor()) return this.render();
    if (this.savedConfig && JSON.stringify(this.status.config) !== this.savedConfig &&
        !window.confirm("Les modifications non enregistrées seront perdues. Changer d'appareil ?")) {
      const picker = this.shadowRoot.querySelector("[data-device-picker]");
      if (picker) picker.value = this.deviceId;
      return;
    }
    await this.fetch(nextId);
  }

  get items() { return this.status?.config?.items || []; }
  get selected() { return this.items.find((item) => item.id === this.selectedId) || null; }
  isFolder(item) { return this.items.some((i) => i.parent === item.id); }

  render() {
    const count = this.items.length;
    const sync = this.status?.sync || "not_synced";
    const badge = sync === "ok" ? "Synchronisé" : sync === "error" ? "Hors ligne" : "Non synchronisé";
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><div class="wrap">
      <div class="top">
        <div>
          <h1>HA Menu C3 <small class="sub">v0.5.4</small></h1>
          <p class="sub">Menus, actions et LED</p>
        </div>
        <div class="actions">
          <label class="device-picker">Appareil
            <select data-device-picker="true" aria-label="Appareil ESPHome">
              ${(this.devices.length ? this.devices : [{entry_id:this.deviceId || "", name:this.status?.device || "ha-menu-c3"}])
                .map(d=>`<option value="${esc(d.entry_id)}" ${d.entry_id === this.deviceId ? "selected" : ""}>${esc(d.name)}</option>`).join("")}
            </select>
          </label>
          <span class="pill ${esc(sync)}">${badge}</span>
          <button class="btn" data-op="identify">Identifier</button>
          <button class="btn" data-op="sync">↻ Synchroniser</button>
          <button class="btn primary" data-op="save">Enregistrer</button>
        </div>
      </div>
      <div id="notice-host"></div>
      <nav class="tabs">
        <button class="btn tab ${this.activeTab === "menus" ? "active" : ""}" data-tab="menus">Menus</button>
        <button class="btn tab ${this.activeTab === "config" ? "active" : ""}" data-tab="config">Réglages et état</button>
      </nav>
      ${this.activeTab === "menus" ? `
      <div class="columns">
        <section class="panel">
          <div class="panel-head"><h2>Arborescence</h2><span class="pill">${count}/32</span></div>
          <div id="tree"></div>
          <div class="small-actions">
            <button class="btn" data-op="add-root" ${count >= 32 ? "disabled" : ""}>+ Entrée</button>
            <button class="btn" data-op="add-folder" ${count >= 32 ? "disabled" : ""}>+ Sous-menu</button>
          </div>
          <p class="hint meta">Glisser pour déplacer. → place sous l'entrée précédente ; ← remonte d'un niveau. « À propos » reste en dernier.</p>
        </section>
        <div>
          <section class="panel"><div class="panel-head"><h2>Éditeur d'entrée</h2></div><div id="editor"></div></section>
          <section class="panel" style="margin-top:16px"><h2>LED RGB permanente</h2><div id="led"></div></section>
        </div>
      </div>` : `
      <section class="panel">
        <h2>Réglages</h2>
        <div id="settings"></div>
        <div class="small-actions"><button class="btn" data-op="identify">Identifier (LED violette)</button></div>
      </section>
      <section class="panel" style="margin-top:16px">
        <div class="panel-head"><h2>État de l'appareil</h2><button class="btn" data-op="refresh">↻ Actualiser</button></div>
        <div id="diagnostics"></div>
      </section>`}
    </div>`;
    this.renderNotice();
    this.renderTree();
    this.renderEditor();
    this.renderLed();
    this.renderSettings();
    this.renderDiagnostics();
  }

  renderNotice() {
    const host = this.shadowRoot.querySelector("#notice-host");
    if (!host) return;
    const backendError = this.status?.sync === "error" && this.status?.error
      ? `Dernière synchronisation : ${this.status.error}` : "";
    const msg = this.notice || backendError;
    host.innerHTML = msg ? `<div class="notice ${esc(this.noticeType || (backendError ? "error" : ""))}">${esc(msg)}</div>` : "";
  }

  renderTree() {
    const host = this.shadowRoot.querySelector("#tree");
    if (!host) return;
    if (!this.items.length) {
      host.innerHTML = `<div class="empty">Menu vide. Ajoute une première entrée.</div><div class="tree-system">ⓘ À propos <small>(système, dernier)</small></div>`;
      return;
    }
    const rows = [];
    const walk = (parent, level) => {
      for (const item of this.items.filter((i) => i.parent === parent)) {
        const folder = this.isFolder(item);
        const siblings = this.items.filter(i=>i.parent===item.parent);
        const prev = siblings[siblings.findIndex(i=>i.id===item.id)-1];
        const canIndent = !!prev && !prev.service && !this.isDescendant(prev.id,item.id);
        rows.push(`<div role="button" tabindex="0" draggable="true" data-select="${esc(item.id)}" class="tree-row ${item.id === this.selectedId ? "active" : ""}" style="padding-left:${9 + level * 16}px">
          <span class="tree-handle" aria-label="Déplacer">⠿</span><span class="tree-glyph">${folder ? "▸" : "•"}</span>
          <span class="tree-item">${esc(item.label)}<small>${folder ? "Sous-menu" : esc(item.service || "Action non configurée")}</small></span>
          <span class="tree-nest"><button type="button" data-tree-move="outdent" data-tree-id="${esc(item.id)}" title="Sortir du sous-menu" aria-label="Sortir ${esc(item.label)} du sous-menu" ${item.parent ? "" : "disabled"}>←</button>
          <button type="button" data-tree-move="indent" data-tree-id="${esc(item.id)}" title="Placer sous l'entrée précédente" aria-label="Placer ${esc(item.label)} dans le sous-menu précédent" ${canIndent ? "" : "disabled"}>→</button></span>
        </div>`);
        walk(item.id, level+1);
      }
    };
    walk("", 0);
    host.innerHTML = `<div class="tree">${rows.join("")}</div>
      <div class="tree-root-drop" data-drop-root="true">↳ Déposer ici pour déplacer à la racine (en dernier)</div>
      <div class="tree-system">ⓘ À propos <small>(système, dernier)</small></div>`;
  }

  renderEditor() {
    const host = this.shadowRoot.querySelector("#editor");
    if (!host) return;
    const item = this.selected;
    if (!item) {
      host.innerHTML = `<div class="empty">Sélectionne une entrée.</div>`;
      return;
    }
    const folder = this.isFolder(item);
    // Search is rendered as a filtered list so friendly names (including plugs) are discoverable.
    const parentChoices = [`<option value="">Racine</option>`, ...this.items
      .filter((i)=> i.id !== item.id && !this.isDescendant(i.id, item.id))
      .map((i) => `<option value="${esc(i.id)}" ${item.parent===i.id ? "selected" : ""}>${esc(i.label)}</option>`)].join("");
    this.editJson = JSON.stringify(item.data || {}, null, 2);
    host.innerHTML = `
      <div class="form-grid">
        <div class="field"><label>Nom affiché sur l'OLED</label><input data-edit="label" maxlength="64" value="${esc(item.label)}"></div>
        <div class="field"><label>Menu parent</label><select data-edit="parent">${parentChoices}</select></div>
      </div>
      <div class="field"><label>Identifiant (stable)</label><input value="${esc(item.id)}" disabled><div class="hint">Identifiant conservé si le nom change.</div></div>
      <div class="section">
        <div class="field">
          <label>Action Home Assistant</label>
          <select data-edit="preset" ${folder ? "disabled" : ""}>
            <option value="">Aucune / dossier</option>
            <option value="light.toggle">Basculer une lumière</option>
            <option value="light.turn_on">Allumer une lumière</option>
            <option value="light.turn_off">Éteindre une lumière</option>
            <option value="switch.toggle">Basculer une prise / un interrupteur</option>
            <option value="switch.turn_on">Allumer une prise / un interrupteur</option>
            <option value="switch.turn_off">Éteindre une prise / un interrupteur</option>
            <option value="homeassistant.toggle">Basculer une entité (universel)</option>
            <option value="climate.turn_on">Activer un thermostat</option>
            <option value="climate.turn_off">Arrêter un thermostat</option>
            <option value="humidifier.toggle">Basculer un humidificateur</option>
            <option value="humidifier.turn_on">Activer un humidificateur</option>
            <option value="humidifier.turn_off">Arrêter un humidificateur</option>
            <option value="cover.open_cover">Ouvrir un volet / portail</option>
            <option value="cover.close_cover">Fermer un volet / portail</option>
            <option value="script.turn_on">Lancer un script</option>
            <option value="scene.turn_on">Activer une scène</option>
            <option value="custom">Autre action...</option>
          </select>
          ${folder ? `<div class="hint">Cette entrée contient des enfants : elle fonctionne comme un sous-menu.</div>` : ""}
        </div>
        <div class="field"><label>Service (domaine.action)</label><input data-edit="service" value="${esc(item.service)}" placeholder="light.toggle" ${folder ? "disabled" : ""}></div>
        <div class="field"><label>Entité cible</label>
          <input data-edit="entity_id" data-entity-search="true" autocomplete="off" value="${esc(item.entity_id)}" placeholder="Rechercher par nom ou identifiant (ex : prise, salon...)" ${folder ? "disabled" : ""}>
          <div id="entity-results"></div>
          <div class="hint">Recherche par nom ou ID, prises incluses.</div>
        </div>
        <div class="field"><label>Données supplémentaires (JSON facultatif)</label><textarea data-edit="data" spellcheck="false" ${folder ? "disabled" : ""}>${esc(this.editJson)}</textarea>
          <div class="hint">Exemple : {"brightness_pct": 60}</div>
        </div>
      </div>
      <div id="control-options">${this.renderControlOptions(item, folder)}</div>
      <div class="small-actions">
        <button class="btn" data-op="add-child" ${this.items.length >= 32 ? "disabled" : ""}>+ Ajouter dans ce menu</button>
        <button class="btn" data-op="move-up">↑ Monter</button>
        <button class="btn" data-op="move-down">↓ Descendre</button>
        <button class="btn danger" data-op="delete">Supprimer</button>
      </div>`;
    const select = host.querySelector('[data-edit="preset"]');
    if (select) select.value = ["", "light.toggle", "light.turn_on", "light.turn_off", "switch.toggle", "switch.turn_on", "switch.turn_off", "homeassistant.toggle", "cover.open_cover", "cover.close_cover", "script.turn_on", "scene.turn_on", "climate.turn_on", "climate.turn_off", "humidifier.toggle", "humidifier.turn_on", "humidifier.turn_off"].includes(item.service) ? item.service : "custom";
  }

  refreshControlOptions() {
    const host = this.shadowRoot.querySelector("#control-options");
    if (host && this.selected) host.innerHTML =
      this.renderControlOptions(this.selected, this.isFolder(this.selected));
  }

  renderControlOptions(item, folder) {
    if (folder) return "";
    const entityId = (item.entity_id || "").trim();
    const domain = entityId.split(".")[0];
    const live = this._hass?.states?.[entityId];
    const attrs = live?.attributes || {};
    const colorModes = attrs.supported_color_modes || [];
    const features = Number(attrs.supported_features || 0);
    const options = {
      light: [
        ["brightness", "Intensité (0–100 %)", colorModes.some(m => m !== "onoff")],
        ["color_temp", "Température (K)", colorModes.includes("color_temp")],
        ["color", "Couleur", colorModes.some(m => ["hs","xy","rgb","rgbw","rgbww"].includes(m))],
      ],
      climate: [
        ["temperature", "Température cible", !!(features & 1)],
        ["hvac_mode", "Mode du thermostat", (attrs.hvac_modes || []).length > 0],
      ],
      humidifier: [
        ["humidity", "Humidité cible", !!live],
        ["humidifier_mode", "Mode", !!(features & 1) && (attrs.available_modes || []).length > 0],
      ],
    }[domain] || [];
    if (!options.length) return `<div class="section"><div class="field">
      <label>Réglages par appui long</label>
      <p class="hint">Sélectionne une lampe, un thermostat ou un humidificateur pour régler ses paramètres depuis l'OLED.</p>
    </div></div>`;
    return `<div class="section"><div class="field"><label>Réglages par appui long</label>
      <p class="hint">Coche les fonctions voulues et clique sur « Appliquer les réglages ». Le clic court garde l'action ci-dessus.</p>
      ${!live ? `<p class="hint">Entité introuvable dans les états Home Assistant. Vérifie son identifiant.</p>` : ""}
      <div class="control-list">${options.map(([key,label,supported])=>`<label class="control-check ${supported?"":"unsupported"}">
        <input type="checkbox" data-control="${esc(key)}" ${(item.controls || {})[key] ? "checked" : ""} ${supported ? "" : "disabled"}>
        <span>${esc(label)}${supported ? "" : " · indisponible"}</span>
      </label>`).join("")}</div>
      <button type="button" class="btn" data-op="apply-controls" style="margin-top:10px">Appliquer les réglages</button>
    </div></div>`;
  }

  renderEntityResults(query="") {
    const host = this.shadowRoot.querySelector("#entity-results");
    if (!host || !query.trim()) {
      if (host) host.innerHTML = "";
      return;
    }
    const normalized = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const needle = normalized(query.trim());
    const domain = (this.selected?.service || "").split(".")[0];
    const states = Object.values(this._hass?.states || {}).filter((state) => {
      const name = state.attributes?.friendly_name || "";
      return normalized(`${state.entity_id} ${name} ${state.attributes?.device_class || ""}`).includes(needle);
    });
    states.sort((a,b) => {
      const rank = (entity) => domain === "homeassistant" || !domain || entity.entity_id.startsWith(domain + ".") ? 0 : 1;
      return rank(a)-rank(b) || (a.attributes?.friendly_name || a.entity_id).localeCompare(b.attributes?.friendly_name || b.entity_id);
    });
    host.innerHTML = states.length ? `<div class="entity-results">${states.slice(0, 60).map((state) => `
      <button type="button" class="entity-option" data-entity-select="${esc(state.entity_id)}">
        <span>${esc(state.attributes?.friendly_name || state.entity_id)}<small>${esc(state.entity_id)} · ${esc(state.state)}</small></span>
      </button>`).join("")}</div>${states.length > 60 ? `<div class="hint">${states.length} résultats : affine la recherche.</div>` : ""}`
      : `<p class="hint">Aucune entité trouvée. Tu peux toujours saisir son identifiant exact.</p>`;
  }

  renderSettings() {
    const host = this.shadowRoot.querySelector("#settings");
    if (!host || !this.status) return;
    const seconds = this.status.config.settings?.sleep_seconds ?? 30;
    host.innerHTML = `<div class="field" style="max-width:340px">
      <label>Veille écran et LED (secondes)</label>
      <input type="number" min="0" max="3600" step="1" data-setting="sleep_seconds" value="${esc(seconds)}">
      <div class="hint">0 : toujours allumés. La LED retrouve sa couleur au réveil.</div>
    </div>`;
  }

  renderDiagnostics() {
    const host = this.shadowRoot.querySelector("#diagnostics");
    if (!host || !this.status) return;
    const data = this.status.diagnostics || {};
    const read = (key, fallback="—") => {
      const state = data[key]?.state;
      return state !== undefined && state !== null && state !== "" &&
        !["unknown", "unavailable"].includes(String(state).toLowerCase())
        ? `${state}${data[key].unit ? " " + data[key].unit : ""}` : fallback;
    };
    const uptime = Number(data.uptime?.state);
    const duration = data.uptime?.state !== undefined && data.uptime?.state !== null &&
      Number.isFinite(uptime) && uptime >= 0
      ? `${Math.floor(uptime/3600)} h ${Math.floor(uptime%3600/60)} min`
      : read("uptime");
    const connected = !!this.status.extension_online;
    const rows = [
      ["Wi-Fi", read("wifi")],
      ["Réseau", read("ssid")],
      ["Adresse IP", read("ip")],
      ["Depuis le démarrage", duration],
      ["Connexion HA", connected ? "Connecté" : "Déconnecté"],
      ["Dernière synchro", read("extension_update", this.status.last_sync_at || "—")],
      ["Menu", this.status.sync === "ok" ? "À jour" : this.status.sync === "syncing" ? "En cours" : "Non synchronisé"],
    ];
    const missing = rows.filter(([,value])=>value==="—").length;
    host.innerHTML = `<div class="diagnostics">${rows.map(([key,val])=>
      `<div class="diagnostic ${val==="—" ? "missing" : ""}"><span class="sub">${esc(key)}</span><strong>${esc(val)}</strong></div>`).join("")}</div>
      ${missing ? `<p class="hint meta">Certaines données manquent. Vérifie les entités de diagnostic ESPHome et flashe le firmware 0.4 pour la remontée directe.</p>` : ""}
      ${this.status.error ? `<p class="notice error">${esc(this.status.error)}</p>` : ""}`;
  }

  renderLed() {
    const host = this.shadowRoot.querySelector("#led");
    if (!host || !this.status) return;
    const led = this.status.config.led;
    const opts = Object.values(this._hass?.states || {}).sort((a,b)=> a.entity_id.localeCompare(b.entity_id))
      .map((s)=>`<option value="${esc(s.entity_id)}" label="${esc(s.attributes?.friendly_name || s.entity_id)}"></option>`).join("");
    host.innerHTML = `<div class="field"><label>Entité suivie (facultative)</label><input data-led="entity_id" list="led-ha-entities" autocomplete="off" placeholder="binary_sensor.porte" value="${esc(led.entity_id)}"><datalist id="led-ha-entities">${opts}</datalist><div class="hint">Si vide, la LED garde la couleur active. Sinon elle suit l'état de cette entité.</div></div>
      <div class="field"><label>Valeur considérée comme active</label><input data-led="active_state" value="${esc(led.active_state)}" placeholder="on"></div>
      <div class="led-grid">
        <div class="field"><label>Couleur active</label><input type="color" data-led="on" value="${rgbHex(led.on)}"></div>
        <div class="field"><label>Couleur inactive</label><input type="color" data-led="off" value="${rgbHex(led.off)}"></div>
      </div><div class="hint">La LED revient à cette couleur après une animation.</div>`;
  }

  isDescendant(candidate, ancestor) {
    let item = this.items.find(i=>i.id === candidate);
    const seen = new Set();
    while (item?.parent) {
      if (item.parent === ancestor) return true;
      if (seen.has(item.parent)) return true;
      seen.add(item.parent);
      item = this.items.find(i=>i.id === item.parent);
    }
    return false;
  }

  createItem(parent="", folder=false) {
    if (this.items.length >= 32) return this.show("Le firmware accepte 32 entrées au maximum.", "error");
    const uid = `m_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,6)}`;
    const item = {id:uid, label: folder ? "Nouveau sous-menu" : "Nouvelle action", parent,
      service:"", entity_id:"", data:{}, controls:{}};
    this.items.push(item);
    if (parent) {
      const parentItem = this.items.find(i => i.id === parent);
      if (parentItem) { parentItem.service = ""; parentItem.entity_id = ""; parentItem.data = {}; }
    }
    this.selectedId = uid;
    this.renderTree(); this.renderEditor();
    this.show("Entrée ajoutée. Pense à enregistrer.");
  }

  moveSelected(dir) {
    const item = this.selected;
    if (!item) return;
    const siblings = this.items.filter(i=>i.parent===item.parent).map(i=>i.id);
    const idx=siblings.indexOf(item.id), next=idx+dir;
    if (next<0 || next>=siblings.length) return;
    [siblings[idx],siblings[next]]=[siblings[next],siblings[idx]];
    const order=new Map(siblings.map((id,pos)=>[id,pos]));
    const entries=this.items;
    const walk=(parent)=>{
      let children=entries.filter(i=>i.parent===parent);
      if (parent===item.parent) children=children.sort((a,b)=>order.get(a.id)-order.get(b.id));
      return children.flatMap(child=>[child,...walk(child.id)]);
    };
    this.status.config.items=walk("");
    this.renderTree();
  }

  indentItem(itemId) {
    const item = this.items.find(i=>i.id===itemId);
    if (!item) return false;
    const siblings = this.items.filter(i=>i.parent===item.parent);
    const prev = siblings[siblings.findIndex(i=>i.id===itemId)-1];
    if (!prev) { this.show("Aucune entrée précédente.", "error"); return false; }
    return this.moveTreeItem(itemId, prev.id, "inside");
  }

  outdentItem(itemId) {
    const item = this.items.find(i=>i.id===itemId);
    if (!item || !item.parent) return false;
    return this.moveTreeItem(itemId, item.parent, "after");
  }

  clearDrag() {
    this.dragId = null;
    this.dropTarget = null;
    this.shadowRoot.querySelectorAll(".drop-before,.drop-after,.drop-inside,.dragging")
      .forEach(el => el.classList.remove("drop-before", "drop-after", "drop-inside", "dragging"));
  }

  onDragStart(event) {
    const row = event.target.closest?.("[data-select]");
    if (!row || event.target.closest?.("[data-tree-move]") || !this.status || !this.commitEditor()) {
      event.preventDefault();
      return;
    }
    this.dragId = row.dataset.select;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", this.dragId);
    row.classList.add("dragging");
  }

  onDragOver(event) {
    if (!this.dragId) return;
    const row = event.target.closest?.("[data-select]");
    const root = event.target.closest?.("[data-drop-root]");
    if (!row && !root) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    this.shadowRoot.querySelectorAll(".drop-before,.drop-after,.drop-inside")
      .forEach(el => el.classList.remove("drop-before", "drop-after", "drop-inside"));
    let placement = "root";
    if (row) {
      const rect = row.getBoundingClientRect();
      const ratio = (event.clientY - rect.top) / rect.height;
      const rightSide = event.clientX > rect.left + Math.min(110, rect.width * 0.4);
      placement = ratio < 0.27 ? "before" : ratio > 0.73 ? "after" : (rightSide ? "inside" : "before");
    }
    const target = row || root;
    target.classList.add(placement === "root" ? "drop-inside" : `drop-${placement}`);
    this.dropTarget = {id: row?.dataset.select || "", placement};
  }

  onDrop(event) {
    if (!this.dragId) return;
    event.preventDefault();
    const src = this.dragId;
    const drop = this.dropTarget;
    this.clearDrag();
    if (!drop) return;
    this.moveTreeItem(src, drop.id, drop.placement);
  }

  moveTreeItem(sourceId, targetId, placement) {
    const moved = this.items.find(i => i.id === sourceId);
    const target = this.items.find(i => i.id === targetId);
    if (!moved || (placement !== "root" && !target)) return false;
    if (targetId === sourceId || (targetId && this.isDescendant(targetId, sourceId))) {
      this.show("Déplacement refusé : un menu ne peut pas être placé dans un de ses descendants.", "error");
      return false;
    }
    if (placement === "inside" && target.service) {
      this.show("Cette entrée possède une action. Retire son action avant d'y déposer un sous-menu.", "error");
      return false;
    }
    const newParent = placement === "root" ? "" : placement === "inside" ? targetId : target.parent;
    if (newParent === sourceId || (newParent && this.isDescendant(newParent, sourceId))) {
      this.show("Sous-menu circulaire interdit.", "error");
      return false;
    }
    const oldParent = moved.parent;
    moved.parent = newParent;
    const siblings = this.items.filter(i => i.parent === newParent && i.id !== sourceId).map(i => i.id);
    let index = siblings.length;
    if (placement === "before") index = siblings.indexOf(targetId);
    if (placement === "after") index = siblings.indexOf(targetId) + 1;
    if (index < 0) index = siblings.length;
    siblings.splice(index, 0, sourceId);
    const siblingOrder = new Map(siblings.map((id, pos) => [id, pos]));
    const current = this.items;
    const result = [];
    const visit = (parent) => {
      const children = current.filter(i => i.parent === parent);
      if (parent === newParent) children.sort((a,b) => siblingOrder.get(a.id) - siblingOrder.get(b.id));
      for (const item of children) { result.push(item); visit(item.id); }
    };
    visit("");
    if (result.length !== current.length) {
      moved.parent = oldParent;
      this.show("Arborescence invalide, déplacement annulé.", "error");
      return false;
    }
    this.status.config.items = result;
    this.selectedId = sourceId;
    this.renderTree(); this.renderEditor();
    this.show("Ordre modifié. Pense à enregistrer.");
    return true;
  }

  deleteSelected() {
    const item=this.selected;
    if (!item) return;
    if (!window.confirm(`Supprimer « ${item.label} » et ses sous-entrées ?`)) return;
    const removed = new Set([item.id]);
    let changed=true;
    while(changed) {
      changed=false;
      for(const entry of this.items) if(removed.has(entry.parent) && !removed.has(entry.id)) {removed.add(entry.id);changed=true;}
    }
    this.status.config.items=this.items.filter(i=>!removed.has(i.id));
    this.selectedId=null;
    this.renderTree();this.renderEditor();
  }

  onClick(event) {
    const tab = event.target.closest("[data-tab]");
    if (tab) {
      if (this.activeTab === "menus" && !this.commitEditor()) return;
      this.activeTab = tab.dataset.tab;
      this.render();
      if (this.activeTab === "config") this.refresh();
      return;
    }
    const entityOption = event.target.closest("[data-entity-select]");
    if (entityOption && this.selected) {
      this.selected.entity_id = entityOption.dataset.entitySelect;
      const input = this.shadowRoot.querySelector('[data-edit="entity_id"]');
      if (input) input.value = this.selected.entity_id;
      const domain = this.selected.entity_id.split(".")[0];
      this.selected.controls = Object.fromEntries(Object.entries(this.selected.controls || {})
        .filter(([key]) => ({light:["brightness","color_temp","color"],climate:["temperature","hvac_mode"],humidifier:["humidity","humidifier_mode"]}[domain] || []).includes(key)));
      this.renderEditor();
      return;
    }
    const nestButton = event.target.closest("[data-tree-move]");
    if (nestButton) {
      if (!this.commitEditor()) return;
      const id=nestButton.dataset.treeId;
      if (nestButton.dataset.treeMove === "indent") this.indentItem(id);
      else this.outdentItem(id);
      return;
    }
    const btn=event.target.closest("[data-op]");
    if(btn) {
      const op=btn.dataset.op;
      if(op==="save" || op==="apply-controls") return this.save();
      if(op==="sync") return this.sync();
      if(op==="identify") return this.identify();
      if(op==="refresh") return this.refresh();
      if(op==="add-root") return this.createItem();
      if(op==="add-folder") return this.createItem("",true);
      if(op==="add-child") return this.createItem(this.selectedId);
      if(op==="move-up") return this.moveSelected(-1);
      if(op==="move-down") return this.moveSelected(1);
      if(op==="delete") return this.deleteSelected();
    }
    const row=event.target.closest("[data-select]");
    if(row && row.dataset.select!==this.selectedId) {
      if (!this.commitEditor()) return;
      this.selectedId=row.dataset.select;
      this.renderTree();this.renderEditor();
    }
  }

  commitEditor() {
    const item=this.selected;
    const textarea=this.shadowRoot.querySelector('textarea[data-edit="data"]');
    if(!item || !textarea || textarea.disabled) {this.editJsonError="";return true;}
    try {
      const data=JSON.parse(textarea.value.trim() || "{}");
      if(!data || Array.isArray(data) || typeof data!=="object") throw new Error("un objet JSON est attendu");
      item.data=data;
      this.editJsonError="";
      return true;
    } catch(err) {
      this.editJsonError=`JSON invalide pour « ${item.label} » : ${err.message}`;
      this.show(this.editJsonError,"error");
      return false;
    }
  }

  onInput(event) {
    if (event.target.dataset.control && this.selected) {
      this.setControl(event.target.dataset.control, event.target.checked);
      return;
    }
    if (event.target.dataset.entitySearch) this.renderEntityResults(event.target.value);
    const setting = event.target.dataset.setting;
    if (setting && this.status) {
      const value = Number(event.target.value);
      if (Number.isInteger(value) && value >= 0 && value <= 3600) {
        this.status.config.settings ||= {};
        this.status.config.settings[setting] = value;
      }
    }
    const edit=event.target.dataset.edit;
    const item=this.selected;
    if(item && edit && edit!=="preset" && edit!=="data" && edit!=="parent") {
      item[edit]=event.target.value;
      if(edit==="label") this.renderTree();
      if(edit==="entity_id") this.refreshControlOptions();
    }
    const led=event.target.dataset.led;
    if(led && this.status) {
      this.status.config.led[led]=["on","off"].includes(led) ? hexRgb(event.target.value) : event.target.value;
    }
  }

  setControl(key, checked) {
    const item = this.selected;
    if (!item) return;
    item.controls ||= {};
    if (checked) item.controls[key] = true;
    else delete item.controls[key];
    this.show("Réglages modifiés. Clique sur Appliquer les réglages pour envoyer à l'ESP32.");
  }

  onChange(event) {
    if (event.target.dataset.control && this.selected) {
      this.setControl(event.target.dataset.control, event.target.checked);
      return;
    }
    if (event.target.dataset.devicePicker) {
      this.selectDevice(event.target.value);
      return;
    }
    const edit=event.target.dataset.edit;
    const item=this.selected;
    if(!item || !edit) return;
    if(edit === "entity_id") { this.refreshControlOptions(); return; }
    if(edit==="preset") {
      if(event.target.value!=="custom") {
        item.service=event.target.value;
        this.renderEditor();
      }
    } else if(edit==="parent") {
      if(event.target.value===item.id || this.isDescendant(event.target.value,item.id)) {
        this.show("Sous-menu circulaire interdit.","error");
        this.renderEditor();
        return;
      }
      item.parent=event.target.value;
      if(item.parent) {
        const p=this.items.find(i=>i.id===item.parent);
        if(p) {p.service="";p.entity_id="";p.data={};}
      }
      this.renderTree();
    } else if(edit==="data") this.commitEditor();
  }

  async save() {
    if(this.busy || !this.status) return;
    if(!this.commitEditor()) return;
    this.busy=true; this.show("Enregistrement et synchronisation en cours...");
    try {
      const res=await this.call("ha_menu_c3/save",{entry_id:this.deviceId,config:this.status.config});
      this.status=res;
      this.devices=res.devices || this.devices;
      this.status.config=clone(res.config);
      this.savedConfig=JSON.stringify(res.config);
      this.show(res.sync==="ok" ? `Configuration enregistrée : ${this.items.length} entrées synchronisées.`
        : `Configuration enregistrée dans Home Assistant, mais synchronisation impossible : ${res.error}`, res.sync==="ok"?"success":"error");
      this.render();
    } catch(err) {
      this.show(`Erreur lors de l'enregistrement : ${err.message || err}`,"error");
    } finally { this.busy=false; }
  }

  async sync() {
    if(this.busy || !this.status) return;
    this.busy=true;this.show("Synchronisation ESPHome...");
    try {
      const res=await this.call("ha_menu_c3/sync",{entry_id:this.deviceId});
      this.status.sync=res.sync;this.status.error=res.error;
      this.status.last_sync_at=res.last_sync_at;
      this.status.diagnostics=res.diagnostics;
      this.devices=res.devices || this.devices;
      this.show(res.sync==="ok"?"Menu envoyé à l'ESP32.":`Synchronisation impossible : ${res.error}`,res.sync==="ok"?"success":"error");
      this.render();
    } catch(err) {this.show(`Erreur : ${err.message || err}`,"error");}
    finally {this.busy=false;}
  }

  async refresh() {
    if (this.busy) return;
    try {
      const remote = await this.call("ha_menu_c3/get",{entry_id:this.deviceId});
      // Keep unsaved local edits; refresh only live status and diagnostics.
      this.status.sync = remote.sync;
      this.status.error = remote.error;
      this.status.last_sync_at = remote.last_sync_at;
      this.status.extension_online = remote.extension_online;
      this.status.diagnostics = remote.diagnostics;
      this.devices = remote.devices || this.devices;
      this.renderDiagnostics();
      this.renderNotice();
    } catch(err) { this.show(`Diagnostics indisponibles : ${err.message || err}`, "error"); }
  }

  async identify() {
    try {
      await this.call("ha_menu_c3/identify",{entry_id:this.deviceId});
      this.show("Identification lancée.","success");
    } catch(err) {this.show(`Identification impossible : ${err.message || err}`,"error");}
  }
}

if (!customElements.get("ha-menu-c3-panel")) customElements.define("ha-menu-c3-panel",HAMenuC3Panel);
