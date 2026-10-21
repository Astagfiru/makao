/* Мгновенный поиск по прайсу на демо химчистки. Без JS виден полный прайс по категориям. */
(function () {
  "use strict";
  var box = document.querySelector("[data-price-search]");
  if (!box) return;
  box.hidden = false;
  var input = box.querySelector("[data-q]");
  var count = box.querySelector("[data-count]");
  var empty = document.querySelector("[data-empty]");
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
  var norm = function (s) { return s.toLowerCase().replace(/ё/g, "е"); };

  input.addEventListener("input", function () {
    var words = norm(input.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    groups.forEach(function (group) {
      var any = false;
      group.querySelectorAll("[data-row]").forEach(function (row) {
        var text = norm(row.textContent + " " + group.querySelector("h3").textContent);
        var ok = words.every(function (w) { return text.indexOf(w) !== -1; });
        row.hidden = !ok;
        if (ok) { any = true; shown += 1; }
      });
      group.hidden = !any;
    });
    count.textContent = words.length ? "Найдено: " + shown : "";
    empty.hidden = shown !== 0;
  });
})();
