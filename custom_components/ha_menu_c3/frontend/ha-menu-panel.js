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
    this.selectedId = null;
    this.notice = "";
    this.noticeType = "";
    this.busy = false;
    this.hasLoaded = false;
    this._hass = null;
    this.editJson = "{}";
    this.editJsonError = "";
  }

  set hass(value) {
    this._hass = value;
    if (this.isConnected && !this.hasLoaded) this.fetch();
  }
  get hass() { return this._hass; }

  connectedCallback() {
    this.render();
    if (this._hass && !this.hasLoaded) this.fetch();
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

  async fetch() {
    if (this.hasLoaded || !this._hass) return;
    this.hasLoaded = true;
    try {
      this.status = await this.call("ha_menu_c3/get");
      this.status.config = clone(this.status.config);
      this.render();
    } catch (err) {
      this.hasLoaded = false;
      this.render();
      this.show(`Impossible de charger l'intégration : ${err.message || err}`, "error");
    }
  }

  get items() { return this.status?.config?.items || []; }
  get selected() { return this.items.find((item) => item.id === this.selectedId) || null; }
  isFolder(item) { return this.items.some((i) => i.parent === item.id); }

  render() {
    const count = this.items.length;
    const sync = this.status?.sync || "not_synced";
    const badge = sync === "ok" ? "Synchronisé" : sync === "error" ? "Hors ligne / erreur" : "Non synchronisé";
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><div class="wrap">
      <div class="top">
        <div>
          <h1>HA Menu C3</h1>
          <p class="sub">Configuration des menus, actions et couleurs de la LED · <b>${esc(this.status?.device || "ha-menu-c3")}</b></p>
        </div>
        <div class="actions">
          <span class="pill ${esc(sync)}">${badge}</span>
          <button class="btn" data-op="identify">◉ Identifier</button>
          <button class="btn" data-op="sync">↻ Synchroniser</button>
          <button class="btn primary" data-op="save">Enregistrer</button>
        </div>
      </div>
      <div id="notice-host"></div>
      <div class="columns">
        <section class="panel">
          <div class="panel-head"><h2>Arborescence</h2><span class="pill">${count}/32</span></div>
          <div id="tree"></div>
          <div class="small-actions">
            <button class="btn" data-op="add-root" ${count >= 32 ? "disabled" : ""}>+ Entrée</button>
            <button class="btn" data-op="add-folder" ${count >= 32 ? "disabled" : ""}>+ Sous-menu</button>
          </div>
          <p class="hint meta">Sélectionne un item pour l'éditer. Les flèches changent son ordre dans le menu. Un sous-menu doit contenir au moins une entrée pour s'ouvrir avec le firmware V4.</p>
        </section>
        <div>
          <section class="panel"><div class="panel-head"><h2>Éditeur d'entrée</h2></div><div id="editor"></div></section>
          <section class="panel" style="margin-top:16px"><h2>LED RGB permanente</h2><div id="led"></div></section>
        </div>
      </div>
    </div>`;
    this.renderNotice();
    this.renderTree();
    this.renderEditor();
    this.renderLed();
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
      host.innerHTML = `<div class="empty">Menu vide. Ajoute une première entrée.</div>`;
      return;
    }
    const rows = [];
    const walk = (parent, level) => {
      for (const item of this.items.filter((i) => i.parent === parent)) {
        const folder = this.isFolder(item);
        rows.push(`<div role="button" tabindex="0" data-select="${esc(item.id)}" class="tree-row ${item.id === this.selectedId ? "active" : ""}" style="padding-left:${9 + level * 16}px">
          <span class="tree-glyph">${folder ? "▸" : "•"}</span>
          <span class="tree-item">${esc(item.label)}<small>${folder ? "Sous-menu" : esc(item.service || "Action non configurée")}</small></span>
        </div>`);
        walk(item.id, level+1);
      }
    };
    walk("", 0);
    host.innerHTML = `<div class="tree">${rows.join("")}</div>`;
  }

  renderEditor() {
    const host = this.shadowRoot.querySelector("#editor");
    if (!host) return;
    const item = this.selected;
    if (!item) {
      host.innerHTML = `<div class="empty">Clique sur une entrée pour configurer son intitulé, l'action Home Assistant et sa position.</div>`;
      return;
    }
    const folder = this.isFolder(item);
    const entityOptions = Object.values(this._hass?.states || {})
      .sort((a,b) => a.entity_id.localeCompare(b.entity_id))
      .map((state) => `<option value="${esc(state.entity_id)}" label="${esc(state.attributes?.friendly_name || state.entity_id)}"></option>`).join("");
    const parentChoices = [`<option value="">Racine</option>`, ...this.items
      .filter((i)=> i.id !== item.id && !this.isDescendant(i.id, item.id))
      .map((i) => `<option value="${esc(i.id)}" ${item.parent===i.id ? "selected" : ""}>${esc(i.label)}</option>`)].join("");
    this.editJson = JSON.stringify(item.data || {}, null, 2);
    host.innerHTML = `
      <div class="form-grid">
        <div class="field"><label>Nom affiché sur l'OLED</label><input data-edit="label" maxlength="64" value="${esc(item.label)}"></div>
        <div class="field"><label>Menu parent</label><select data-edit="parent">${parentChoices}</select></div>
      </div>
      <div class="field"><label>Identifiant (stable)</label><input value="${esc(item.id)}" disabled><div class="hint">Référence utilisée par l'ESP32. Elle reste identique après un renommage.</div></div>
      <div class="section">
        <div class="field">
          <label>Action Home Assistant</label>
          <select data-edit="preset" ${folder ? "disabled" : ""}>
            <option value="">Aucune / dossier</option>
            <option value="light.toggle">Basculer une lumière</option>
            <option value="light.turn_on">Allumer une lumière</option>
            <option value="light.turn_off">Éteindre une lumière</option>
            <option value="switch.toggle">Basculer un interrupteur</option>
            <option value="cover.open_cover">Ouvrir un volet / portail</option>
            <option value="cover.close_cover">Fermer un volet / portail</option>
            <option value="script.turn_on">Lancer un script</option>
            <option value="scene.turn_on">Activer une scène</option>
            <option value="custom">Autre action...</option>
          </select>
          ${folder ? `<div class="hint">Cette entrée contient des enfants : elle fonctionne comme un sous-menu.</div>` : ""}
        </div>
        <div class="field"><label>Service (domaine.action)</label><input data-edit="service" value="${esc(item.service)}" placeholder="light.toggle" ${folder ? "disabled" : ""}></div>
        <div class="field"><label>Entité cible</label><input data-edit="entity_id" list="ha-menu-entities" autocomplete="off" value="${esc(item.entity_id)}" placeholder="light.salon" ${folder ? "disabled" : ""}>
          <datalist id="ha-menu-entities">${entityOptions}</datalist>
          <div class="hint">Commence à taper pour rechercher une entité présente dans Home Assistant.</div>
        </div>
        <div class="field"><label>Données supplémentaires (JSON facultatif)</label><textarea data-edit="data" spellcheck="false" ${folder ? "disabled" : ""}>${esc(this.editJson)}</textarea>
          <div class="hint">Exemple : {"brightness_pct": 60}. Utile pour les actions avancées.</div>
        </div>
      </div>
      <div class="small-actions">
        <button class="btn" data-op="add-child" ${this.items.length >= 32 ? "disabled" : ""}>+ Ajouter dans ce menu</button>
        <button class="btn" data-op="move-up">↑ Monter</button>
        <button class="btn" data-op="move-down">↓ Descendre</button>
        <button class="btn danger" data-op="delete">Supprimer</button>
      </div>`;
    const select = host.querySelector('[data-edit="preset"]');
    if (select) select.value = ["", "light.toggle", "light.turn_on", "light.turn_off", "switch.toggle", "cover.open_cover", "cover.close_cover", "script.turn_on", "scene.turn_on"].includes(item.service) ? item.service : "custom";
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
      </div><div class="hint">Les animations temporaires bleu/vert/rouge sont gérées directement par le firmware V4 et reviennent ensuite à cette couleur permanente.</div>`;
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
      service:"", entity_id:"", data:{}};
    this.items.push(item);
    if (parent) {
      const parentItem = this.items.find(i => i.id === parent);
      if (parentItem) { parentItem.service = ""; parentItem.entity_id = ""; parentItem.data = {}; }
    }
    this.selectedId = uid;
    this.renderTree(); this.renderEditor();
    this.show("Entrée ajoutée localement. Clique sur Enregistrer pour l'envoyer au C3.");
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
    const btn=event.target.closest("[data-op]");
    if(btn) {
      const op=btn.dataset.op;
      if(op==="save") return this.save();
      if(op==="sync") return this.sync();
      if(op==="identify") return this.identify();
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
    const edit=event.target.dataset.edit;
    const item=this.selected;
    if(item && edit && edit!=="preset" && edit!=="data" && edit!=="parent") {
      item[edit]=event.target.value;
      if(edit==="label") this.renderTree();
    }
    const led=event.target.dataset.led;
    if(led && this.status) {
      this.status.config.led[led]=["on","off"].includes(led) ? hexRgb(event.target.value) : event.target.value;
    }
  }

  onChange(event) {
    const edit=event.target.dataset.edit;
    const item=this.selected;
    if(!item || !edit) return;
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
      const res=await this.call("ha_menu_c3/save",{config:this.status.config});
      this.status=res;
      this.status.config=clone(res.config);
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
      const res=await this.call("ha_menu_c3/sync");
      this.status.sync=res.sync;this.status.error=res.error;
      this.show(res.sync==="ok"?"Menu envoyé à l'ESP32.":`Synchronisation impossible : ${res.error}`,res.sync==="ok"?"success":"error");
      this.render();
    } catch(err) {this.show(`Erreur : ${err.message || err}`,"error");}
    finally {this.busy=false;}
  }

  async identify() {
    try {
      await this.call("ha_menu_c3/identify");
      this.show("Animation violette demandée au C3.","success");
    } catch(err) {this.show(`Identification impossible : ${err.message || err}`,"error");}
  }
}

if (!customElements.get("ha-menu-c3-panel")) customElements.define("ha-menu-c3-panel",HAMenuC3Panel);
