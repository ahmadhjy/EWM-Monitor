(function () {
  "use strict";

  const adminRoot = (window.location.pathname.match(/^(.*\/admin\/)/) || [])[1] || "/admin/";
  const libraryUrl = `${adminRoot}content/mediaasset/picker/`;
  const uploadUrl = `${libraryUrl}upload/`;
  let dialog;
  let state;
  let searchTimer;

  const csrfToken = () => {
    const formToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
    if (formToken) return formToken;
    const cookie = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
  };

  const escapeText = (value) => String(value || "");

  function buildDialog() {
    dialog = document.createElement("dialog");
    dialog.className = "ewm-media-picker";
    dialog.setAttribute("aria-labelledby", "ewm-media-title");
    dialog.innerHTML = `
      <div class="ewm-media-picker__shell">
        <header class="ewm-media-picker__header">
          <div><span>Editorial media</span><h2 id="ewm-media-title">Choose an image</h2></div>
          <button type="button" class="ewm-media-picker__close" aria-label="Close media library">×</button>
        </header>
        <div class="ewm-media-picker__toolbar">
          <label><span class="sr-only">Search media</span><input type="search" data-media-search placeholder="Search by title, alt text, caption or credit"></label>
          <button type="button" class="ewm-media-picker__upload-toggle">Upload new image</button>
        </div>
        <form class="ewm-media-picker__upload" hidden>
          <div class="ewm-media-picker__drop"><input type="file" name="file" accept="image/*" required><span>Choose an image from your computer</span></div>
          <label>Title<input type="text" name="title" maxlength="180" required></label>
          <label>Alt text<input type="text" name="alt_text" maxlength="220" placeholder="Describe the image for readers and search engines"></label>
          <label>Caption<textarea name="caption" rows="2"></textarea></label>
          <div class="ewm-media-picker__upload-actions"><button type="button" data-upload-cancel>Cancel</button><button type="submit">Upload to library</button></div>
        </form>
        <div class="ewm-media-picker__content">
          <section class="ewm-media-picker__library" aria-label="Media library">
            <div class="ewm-media-picker__status" role="status" aria-live="polite"></div>
            <div class="ewm-media-picker__grid"></div>
            <button type="button" class="ewm-media-picker__more" hidden>Load more</button>
          </section>
          <aside class="ewm-media-picker__details">
            <div class="ewm-media-picker__empty">Select an image to see its details.</div>
            <div class="ewm-media-picker__selection" hidden>
              <img alt="">
              <h3></h3>
              <label>Alt text<input type="text" maxlength="220" data-selected-alt></label>
              <p class="ewm-media-picker__caption"></p>
              <small class="ewm-media-picker__url"></small>
            </div>
          </aside>
        </div>
        <footer class="ewm-media-picker__footer">
          <span>Alt text is saved to the library and inserted into the article.</span>
          <div><button type="button" data-media-cancel>Cancel</button><button type="button" class="ewm-media-picker__insert" disabled>Insert image</button></div>
        </footer>
      </div>`;
    document.body.append(dialog);

    dialog.querySelector(".ewm-media-picker__close").addEventListener("click", closeDialog);
    dialog.querySelector("[data-media-cancel]").addEventListener("click", closeDialog);
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog();
    });
    dialog.querySelector("[data-media-search]").addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => loadAssets(true), 250);
    });
    dialog.querySelector(".ewm-media-picker__more").addEventListener("click", () => {
      state.page += 1;
      loadAssets(false);
    });
    dialog.querySelector(".ewm-media-picker__upload-toggle").addEventListener("click", () => setUploadOpen(true));
    dialog.querySelector("[data-upload-cancel]").addEventListener("click", () => setUploadOpen(false));
    dialog.querySelector(".ewm-media-picker__upload").addEventListener("submit", uploadAsset);
    dialog.querySelector('input[name="file"]').addEventListener("change", populateUploadTitle);
    dialog.querySelector(".ewm-media-picker__insert").addEventListener("click", insertSelected);
  }

  function setStatus(message, isError = false) {
    const status = dialog.querySelector(".ewm-media-picker__status");
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function setUploadOpen(open) {
    const form = dialog.querySelector(".ewm-media-picker__upload");
    form.hidden = !open;
    dialog.querySelector(".ewm-media-picker__upload-toggle").setAttribute("aria-expanded", String(open));
    if (open) form.querySelector('input[name="file"]').focus();
  }

  function populateUploadTitle(event) {
    const file = event.target.files[0];
    if (!file) return;
    const title = file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").trim();
    dialog.querySelector('input[name="title"]').value = title;
  }

  async function loadAssets(reset) {
    if (state.loading) return;
    state.loading = true;
    if (reset) {
      state.page = 1;
      state.items = [];
      state.selected = null;
      renderSelection();
    }
    const query = dialog.querySelector("[data-media-search]").value.trim();
    setStatus("Loading media…");
    try {
      const response = await fetch(`${libraryUrl}?q=${encodeURIComponent(query)}&page=${state.page}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error("The media library could not be loaded.");
      const data = await response.json();
      state.items = reset ? data.items : state.items.concat(data.items);
      state.hasMore = data.has_more;
      renderGrid();
      setStatus(data.total ? `${data.total} image${data.total === 1 ? "" : "s"} in this view` : "No images found.");
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      state.loading = false;
    }
  }

  function renderGrid() {
    const grid = dialog.querySelector(".ewm-media-picker__grid");
    grid.replaceChildren();
    state.items.forEach((asset) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ewm-media-picker__asset";
      button.dataset.assetId = asset.id;
      button.setAttribute("aria-label", `Select ${asset.title}`);
      const image = document.createElement("img");
      image.src = asset.url;
      image.alt = "";
      image.loading = "lazy";
      const label = document.createElement("span");
      label.textContent = escapeText(asset.title);
      button.append(image, label);
      button.addEventListener("click", () => selectAsset(asset));
      button.addEventListener("dblclick", () => {
        selectAsset(asset);
        insertSelected();
      });
      grid.append(button);
    });
    const more = dialog.querySelector(".ewm-media-picker__more");
    more.hidden = !state.hasMore;
  }

  function selectAsset(asset) {
    state.selected = asset;
    dialog.querySelectorAll(".ewm-media-picker__asset").forEach((button) => {
      button.classList.toggle("is-selected", Number(button.dataset.assetId) === asset.id);
    });
    renderSelection();
  }

  function renderSelection() {
    const empty = dialog.querySelector(".ewm-media-picker__empty");
    const selection = dialog.querySelector(".ewm-media-picker__selection");
    const insert = dialog.querySelector(".ewm-media-picker__insert");
    empty.hidden = Boolean(state.selected);
    selection.hidden = !state.selected;
    insert.disabled = !state.selected;
    if (!state.selected) return;
    selection.querySelector("img").src = state.selected.url;
    selection.querySelector("h3").textContent = state.selected.title;
    selection.querySelector("[data-selected-alt]").value = state.selected.alt_text || "";
    selection.querySelector(".ewm-media-picker__caption").textContent = state.selected.caption || "No caption";
    selection.querySelector(".ewm-media-picker__url").textContent = state.selected.url;
  }

  async function uploadAsset(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Uploading…";
    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
        body: new FormData(form),
      });
      const data = await response.json();
      if (!response.ok) {
        const messages = Object.values(data.errors || {}).flat().map((item) => item.message).join(" ");
        throw new Error(messages || data.error || "Upload failed.");
      }
      state.items.unshift(data.item);
      renderGrid();
      selectAsset(data.item);
      form.reset();
      setUploadOpen(false);
      setStatus("Image uploaded. Review the alt text, then insert it.");
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      submit.disabled = false;
      submit.textContent = "Upload to library";
    }
  }

  async function insertSelected() {
    if (!state.selected) return;
    const alt = dialog.querySelector("[data-selected-alt]").value.trim();
    const insert = dialog.querySelector(".ewm-media-picker__insert");
    insert.disabled = true;
    insert.textContent = "Inserting…";
    try {
      if (alt !== (state.selected.alt_text || "")) {
        const formData = new FormData();
        formData.append("alt_text", alt);
        const response = await fetch(`${libraryUrl}${state.selected.id}/alt/`, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
          body: formData,
        });
        if (!response.ok) throw new Error("The alt text could not be saved.");
      }
      state.callback(state.selected.url, { alt, title: state.selected.title });
      closeDialog();
    } catch (error) {
      setStatus(error.message, true);
      insert.disabled = false;
      insert.textContent = "Insert image";
    }
  }

  function closeDialog() {
    if (dialog?.open) dialog.close();
    state = null;
  }

  window.ewmMediaPicker = function (callback, value, meta) {
    if (meta.filetype !== "image") return;
    if (!dialog) buildDialog();
    state = { callback, items: [], selected: null, page: 1, hasMore: false, loading: false };
    dialog.querySelector("[data-media-search]").value = "";
    setUploadOpen(false);
    renderGrid();
    renderSelection();
    dialog.showModal();
    loadAssets(true);
  };
})();
