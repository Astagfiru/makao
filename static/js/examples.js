/* Сайты-примеры: автоподбор времени при смене услуги/дня, живой итог корзины, поиск по прайсу.
   Без JS всё работает обычными формами. */
(function () {
  "use strict";

  /* Запись: при смене услуги или дня сразу показать свободное время */
  document.querySelectorAll("[data-autosubmit]").forEach(function (form) {
    form.addEventListener("change", function () { form.submit(); });
  });

  /* Корзина и калькулятор: итог считается сразу. Скидки — как на сервере: 15% от 5 зимних вещей (химчистка),
     каждый 6-й кофе в подарок и −15% на кофе в свою тару (кофейня) */
  document.querySelectorAll("[data-cart]").forEach(function (form) {
    var summary = form.querySelector(".ex-summary");
    var isDryclean = document.body.classList.contains("demo-dryclean");
    var isCafe = document.body.classList.contains("demo-cafe");
    var stamps = parseInt(form.dataset.stamps, 10) || 0;
    var ownCup = form.querySelector("[data-own-cup]");
    var money = function (n) { return n.toLocaleString("ru-RU").replace(/ /g, " ") + " ₽"; };
    function recalc() {
      var total = 0, winter = 0, unknown = 0, lines = [], cups = [], discounts = [];
      form.querySelectorAll("[data-row]").forEach(function (row) {
        var qty = parseInt(row.querySelector("input").value, 10) || 0;
        row.classList.toggle("is-on", qty > 0);
        if (qty <= 0) return;
        var price = row.dataset.price === "" ? null : parseInt(row.dataset.price, 10);
        var name = row.querySelector(".ex-cart-name").textContent;
        lines.push([name.length > 38 ? name.slice(0, 37) + "…" : name, qty, price === null ? null : price * qty]);
        if (price === null) unknown += 1; else total += price * qty;
        if (row.dataset.winter === "1") winter += qty;
        if (row.dataset.coffee === "1" && price !== null) for (var i = 0; i < qty; i++) cups.push(price);
      });
      if (isDryclean && winter >= 5) discounts.push(["Скидка 15% за " + winter + " зимних вещей", Math.round(total * 0.15)]);
      if (isCafe) {
        cups.sort(function (a, b) { return a - b; });
        var gifts = Math.floor((stamps + cups.length) / 6) - Math.floor(stamps / 6);
        var sum = function (list) { return list.reduce(function (a, b) { return a + b; }, 0); };
        if (gifts) discounts.push(["Каждый 6-й кофе в подарок: " + gifts + " шт.", sum(cups.slice(0, gifts))]);
        if (ownCup && ownCup.checked && cups.length > gifts) discounts.push(["Своя тара: −15% на кофе", Math.round(sum(cups.slice(gifts)) * 0.15)]);
      }
      var discount = discounts.reduce(function (a, d) { return a + d[1]; }, 0);
      var html = '<p class="ex-summary-title">Итого</p>';
      if (!lines.length) {
        html += '<p class="ex-muted">Пока ничего не выбрано.</p>';
      } else {
        html += "<ul role=\"list\">" + lines.map(function (l) {
          return "<li><span></span><strong>" + (l[2] === null ? "по запросу" : money(l[2])) + "</strong></li>";
        }).join("") + "</ul>";
        discounts.forEach(function (d) { html += '<p class="ex-discount">' + d[0] + ": −" + money(d[1]) + "</p>"; });
        if (isCafe) html += '<p class="ex-muted">Штампов на карте гостя после заказа: ' + ((stamps + cups.length) % 6) + " из 6</p>";
        if (!discount && isDryclean && winter > 0) html += '<p class="ex-muted">Ещё ' + (5 - winter) + " зимн. вещи — и скидка 15%</p>";
        html += '<p class="ex-total">' + money(total - discount) + (unknown ? " <small>+ позиции по запросу</small>" : "") + "</p>";
      }
      html += '<button class="ex-btn" type="submit">Перейти к оформлению</button>';
      summary.innerHTML = html;
      summary.querySelectorAll("li span").forEach(function (span, i) { span.textContent = lines[i][0] + " × " + lines[i][1]; });
    }
    form.addEventListener("input", recalc);
    recalc();
  });

  /* Поиск по прайсу */
  var box = document.querySelector("[data-price-search]");
  if (box) {
    box.hidden = false;
    var input = box.querySelector("input");
    var groups = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
    var norm = function (s) { return s.toLowerCase().replace(/ё/g, "е"); };
    input.addEventListener("input", function () {
      var words = norm(input.value).split(/\s+/).filter(Boolean);
      groups.forEach(function (group) {
        var any = false;
        group.querySelectorAll("[data-row]").forEach(function (row) {
          var ok = words.every(function (w) { return norm(row.textContent + group.dataset.title).indexOf(w) !== -1; });
          row.hidden = !ok;
          any = any || ok;
        });
        group.hidden = !any;
      });
    });
  }
})();
