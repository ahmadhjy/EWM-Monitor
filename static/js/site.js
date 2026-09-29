(() => {
  const rtl = document.documentElement.dir === "rtl";
  const hero = document.querySelector("[data-hero-motion]");
  if (hero) {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let inView = true;
    const syncMotion = () => {
      hero.classList.toggle("is-motion-paused", reducedMotion.matches);
      hero.classList.toggle("is-motion-idle", !inView || document.hidden);
    };
    reducedMotion.addEventListener("change", syncMotion);
    document.addEventListener("visibilitychange", syncMotion);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([entry]) => {
        inView = entry.isIntersecting;
        syncMotion();
      }).observe(hero);
    }
    syncMotion();
  }
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navigation = document.querySelector("[data-navigation]");
  const navLabel = navToggle?.querySelector(".sr-only");
  const languageMenu = document.querySelector("[data-language-menu]");
  document.addEventListener("click", (event) => {
    if (languageMenu && !languageMenu.contains(event.target)) languageMenu.open = false;
  });
  const setNavigation = (open) => {
    if (!navToggle || !navigation) return;
    if (open && languageMenu) languageMenu.open = false;
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
      if (window.innerWidth > 1279) setNavigation(false);
      else if (navigation.classList.contains("is-open")) setNavigation(true);
    }, { passive: true });
  }

  document.querySelectorAll("[data-submenu-toggle]").forEach((toggle) => {
    const item = toggle.closest(".nav-item");
    const desktopHover = window.matchMedia("(min-width: 1280px) and (hover: hover) and (pointer: fine)");
    let openedByHover = false;
    let closeTimer;
    const open = () => {
      clearTimeout(closeTimer);
      document.querySelectorAll("[data-submenu-toggle]").forEach((other) => {
        other.setAttribute("aria-expanded", "false");
        other.closest(".nav-item").classList.remove("is-expanded");
      });
      toggle.setAttribute("aria-expanded", "true");
      item.classList.add("is-expanded");
    };
    const close = () => {
      clearTimeout(closeTimer);
      toggle.setAttribute("aria-expanded", "false");
      item.classList.remove("is-expanded");
      openedByHover = false;
    };
    item.addEventListener("pointerenter", (event) => {
      if (!desktopHover.matches || event.pointerType !== "mouse") return;
      clearTimeout(closeTimer);
      if (toggle.getAttribute("aria-expanded") !== "true") {
        open();
        openedByHover = true;
      }
    });
    item.addEventListener("pointerleave", (event) => {
      if (desktopHover.matches && event.pointerType === "mouse") closeTimer = setTimeout(close, 180);
    });
    toggle.addEventListener("click", (event) => {
      // The first mouse click must not undo the menu just opened by hovering.
      if (toggle.getAttribute("aria-expanded") !== "true" || (openedByHover && event.detail > 0)) open();
      else close();
      openedByHover = false;
    });
    item.addEventListener("focusout", (event) => {
      if (!item.contains(event.relatedTarget) && !item.matches(":hover")) close();
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
    if (languageMenu?.open) {
      languageMenu.open = false;
      languageMenu.querySelector("summary").focus({ preventScroll: true });
      return;
    }
    const expanded = navigation?.querySelector('[data-submenu-toggle][aria-expanded="true"]');
    if (expanded) {
      expanded.setAttribute("aria-expanded", "false");
      expanded.closest(".nav-item").classList.remove("is-expanded");
      expanded.focus({ preventScroll: true });
      return;
    }
    if (document.body.classList.contains("nav-open")) navToggle?.focus({ preventScroll: true });
    setNavigation(false);
    if (searchPanel) searchPanel.hidden = true;
  });

  const header = document.querySelector("[data-header]");
  document.addEventListener("click", (event) => {
    if (navigation?.contains(event.target)) return;
    navigation?.querySelectorAll("[data-submenu-toggle]").forEach((toggle) => {
      toggle.setAttribute("aria-expanded", "false");
      toggle.closest(".nav-item").classList.remove("is-expanded");
    });
  });
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
