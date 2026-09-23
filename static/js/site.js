(() => {
  const rtl = document.documentElement.dir === "rtl";
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navigation = document.querySelector("[data-navigation]");
  const navLabel = navToggle?.querySelector(".sr-only");
  const setNavigation = (open) => {
    if (!navToggle || !navigation) return;
    navToggle.setAttribute("aria-expanded", String(open));
    navigation.classList.toggle("is-open", open);
    document.body.classList.toggle("nav-open", open);
    if (open) navigation.style.setProperty("--menu-top", document.querySelector("[data-header]").getBoundingClientRect().bottom + "px");
    if (navLabel) navLabel.textContent = rtl ? (open ? "إغلاق القائمة" : "القائمة") : (open ? "Close menu" : "Menu");
  };
  if (navToggle && navigation) {
    navToggle.addEventListener("click", () => {
      const open = navToggle.getAttribute("aria-expanded") === "true";
      setNavigation(!open);
    });
    navigation.addEventListener("click", (event) => {
      if (event.target.closest("a")) setNavigation(false);
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 900) setNavigation(false);
    }, { passive: true });
  }

  document.querySelectorAll("[data-submenu-toggle]").forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const item = toggle.closest(".nav-item");
      const expanded = toggle.getAttribute("aria-expanded") !== "true";
      document.querySelectorAll("[data-submenu-toggle]").forEach((other) => {
        other.setAttribute("aria-expanded", "false");
        other.closest(".nav-item").classList.remove("is-expanded");
      });
      toggle.setAttribute("aria-expanded", String(expanded));
      item.classList.toggle("is-expanded", expanded);
    });
  });

  const searchToggle = document.querySelector("[data-search-toggle]");
  const searchPanel = document.querySelector("[data-search-panel]");
  if (searchToggle && searchPanel) {
    searchToggle.addEventListener("click", () => {
      setNavigation(false);
      searchPanel.hidden = !searchPanel.hidden;
      if (!searchPanel.hidden) searchPanel.querySelector("input")?.focus();
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (document.body.classList.contains("nav-open")) navToggle?.focus();
    setNavigation(false);
    if (searchPanel) searchPanel.hidden = true;
  });

  const header = document.querySelector("[data-header]");
  const updateHeader = () => header?.classList.toggle("is-scrolled", window.scrollY > 12);
  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });

  const articleBody = document.querySelector("[data-article-body]");
  const toc = document.querySelector("[data-toc]");
  if (articleBody && toc) {
    const headings = [...articleBody.querySelectorAll("h2, h3")];
    if (headings.length) {
      toc.innerHTML = "";
      headings.forEach((heading, index) => {
        if (!heading.id) heading.id = `section-${index + 1}`;
        const link = document.createElement("a");
        link.href = `#${heading.id}`;
        link.textContent = heading.textContent;
        if (heading.tagName === "H3") link.className = "toc-subitem";
        toc.append(link);
      });
    }
  }

  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    }), { rootMargin: "0px 0px 50px 0px", threshold: 0.05 });
    document.querySelectorAll("[data-reveal]").forEach((element) => {
      if (element.getBoundingClientRect().top > window.innerHeight) {
        element.classList.add("reveal-pending");
        observer.observe(element);
      }
    });
  }

  if (articleBody && header) {
    const progress = document.createElement("div");
    progress.className = "article-reading-progress";
    progress.setAttribute("aria-hidden", "true");
    header.append(progress);
    let pending = false;
    const updateProgress = () => {
      const bounds = articleBody.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (window.innerHeight - bounds.top) / bounds.height));
      progress.style.transform = `scaleX(${fraction})`;
      pending = false;
    };
    window.addEventListener("scroll", () => {
      if (!pending) { pending = true; requestAnimationFrame(updateProgress); }
    }, { passive: true });
    updateProgress();
  }

})();
