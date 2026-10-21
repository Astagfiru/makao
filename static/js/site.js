/* Минимум ванильного JS: тема, cookie-плашка, появление блоков, аккордеон этапов,
   подсветка карточек за курсором, Яндекс.Карта по клику. Без JS всё содержимое видно и работает. */
(function () {
  "use strict";
  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function store(key, value) {
    try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { return null; }
    return null;
  }

  /* Тема: солнце ↔ луна, новая тема разливается кругом от кнопки */
  var toggle = document.querySelector("[data-theme-toggle]");
  function syncToggle() {
    if (toggle) toggle.setAttribute("aria-pressed", root.dataset.theme === "frost" ? "true" : "false");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", root.dataset.theme === "frost" ? "#eef4f9" : "#070b16");
  }
  if (toggle) {
    syncToggle();
    toggle.addEventListener("click", function () {
      var next = root.dataset.theme === "frost" ? "night" : "frost";
      var apply = function () { root.dataset.theme = next; store("theme", next); syncToggle(); };
      if (!document.startViewTransition || reduceMotion) { apply(); return; }
      var r = toggle.getBoundingClientRect();
      var x = r.left + r.width / 2, y = r.top + r.height / 2;
      root.style.setProperty("--tx", x + "px");
      root.style.setProperty("--ty", y + "px");
      root.style.setProperty("--tr", Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + "px");
      document.startViewTransition(apply);
    });
  }

  /* Cookie-плашка: поверх страницы, выбор — в localStorage */
  var cookie = document.querySelector("[data-cookie]");
  if (cookie && store("cookie-ok") !== "1") {
    cookie.hidden = false;
    cookie.querySelector("[data-cookie-accept]").addEventListener("click", function () {
      store("cookie-ok", "1");
      cookie.hidden = true;
      document.dispatchEvent(new CustomEvent("cookies:accepted"));
    });
  }

  /* Появление частей каждого раздела: заголовок, текст, картинка — со сдвигом */
  var groups = document.querySelectorAll(".chapter, .page-hero");
  if ("IntersectionObserver" in window && !reduceMotion) {
    groups.forEach(function (group) {
      var parts = group.querySelectorAll("h2, h3, p, li, .btn, .specimen-tile, .folder-tab");
      parts.forEach(function (el, i) {
        if (el.closest(".hero") || el.closest(".folder-body") && i > 40) return;
        el.setAttribute("data-reveal", "");
        el.style.setProperty("--d", Math.min(i % 8, 7) * 70 + "ms");
      });
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    document.querySelectorAll("[data-reveal]").forEach(function (el) { io.observe(el); });
  }

  /* Аккордеон этапов работы */
  document.querySelectorAll("[data-accordion]").forEach(function (list) {
    list.addEventListener("click", function (event) {
      var btn = event.target.closest(".stage-btn");
      if (!btn) return;
      list.querySelectorAll(".stage").forEach(function (stage) {
        var open = stage.contains(btn);
        stage.classList.toggle("is-open", open);
        stage.querySelector(".stage-btn").setAttribute("aria-expanded", open ? "true" : "false");
      });
    });
  });

  /* Подсветка карточек кейсов за курсором */
  document.querySelectorAll("[data-glow]").forEach(function (card) {
    card.addEventListener("pointermove", function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty("--gx", e.clientX - r.left + "px");
      card.style.setProperty("--gy", e.clientY - r.top + "px");
    });
  });

  /* Кнопка тарифа подставляет его в поле «Что нужно» */
  document.querySelectorAll("[data-tariff]").forEach(function (link) {
    link.addEventListener("click", function () {
      var field = document.querySelector("#zayavka textarea");
      if (field && !field.value) field.value = "Интересует тариф «" + link.dataset.tariff + "»";
    });
  });

  /* Яндекс.Карта: грузится только по клику (у Яндекса свои cookie) */
  document.querySelectorAll("[data-map]").forEach(function (box) {
    var btn = box.querySelector("[data-map-load]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var frame = document.createElement("iframe");
      frame.src = box.dataset.src;
      frame.title = "Яндекс.Карта: Якутск";
      frame.loading = "lazy";
      frame.referrerPolicy = "strict-origin-when-cross-origin";
      box.replaceChildren(frame);
      box.classList.add("is-loaded");
    });
  });
})();
