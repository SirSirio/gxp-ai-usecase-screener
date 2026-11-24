// "How it works" page: pick a path through the decision tree (progressive enhancement).
// The tree, its chips and leaves are rendered on the server (app/how_it_works.py); this script draws the
// connectors, lights up the chosen path, plays the example paths and builds the phone stepper from the same
// data. Without JavaScript the text version of the tree below it carries the same content.
(function () {
  "use strict";
  var root = document.querySelector("[data-hiw]");
  if (!root) return;
  var data = JSON.parse(document.getElementById("hiw-data").textContent);
  var tree = root.querySelector("[data-tree]"), svg = tree.querySelector("[data-links]");
  var readout = root.querySelector("[data-readout]"), stepper = root.querySelector("[data-stepper]");
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var NS = "http://www.w3.org/2000/svg";
  var path = [], lit = {}, timers = [];

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function q(sel) { return tree.querySelector(sel); }
  function targetEl(id) { return data.leaves[id] ? q('[data-leaf="' + id + '"]') : q('[data-node="' + id + '"]'); }
  function end() { return path.length ? data.chips[path[path.length - 1]].to : null; }

  // ---------------------------------------------------------------- connectors
  function box(el, base) {
    var r = el.getBoundingClientRect();
    return { l: r.left - base.left, r: r.right - base.left, t: r.top - base.top, b: r.bottom - base.top,
             cx: (r.left + r.right) / 2 - base.left, cy: (r.top + r.bottom) / 2 - base.top };
  }
  function curve(x1, y1, x2, y2) {
    var dx = Math.max(12, (x2 - x1) / 2);
    return "M" + x1 + " " + y1 + " C" + (x1 + dx) + " " + y1 + " " + (x2 - dx) + " " + y2 + " " + x2 + " " + y2;
  }
  function draw() {
    if (!tree.offsetParent) return; // hidden (phone layout): the stepper is shown instead
    var base = tree.getBoundingClientRect();
    svg.setAttribute("viewBox", "0 0 " + base.width + " " + base.height);
    svg.textContent = "";
    Object.keys(data.chips).forEach(function (id) {
      var c = data.chips[id], chipEl = q('[data-chip="' + id + '"]');
      var from = box(q('[data-node="' + c.node + '"]'), base), chip = box(chipEl, base), to = box(targetEl(c.to), base);
      var down = !!chipEl.closest(".is-down");
      var ds = down ? ["M" + from.cx + " " + from.b + " L" + chip.cx + " " + chip.t, "M" + chip.cx + " " + chip.b + " L" + to.cx + " " + to.t]
                    : [curve(from.r, from.cy, chip.l, chip.cy), curve(chip.r, chip.cy, to.l, to.cy)];
      ds.forEach(function (d, k) {
        var p = document.createElementNS(NS, "path");
        p.setAttribute("d", d);
        p.setAttribute("class", "hiw-link");
        p.dataset.link = id;
        p.dataset.part = k ? "out" : "in";
        svg.appendChild(p);
        p.style.setProperty("--len", Math.ceil(p.getTotalLength()) + "px");
      });
    });
    lit = {};
    paint(false);
  }

  // ---------------------------------------------------------------- state
  function paint(animate) {
    var onChips = {}, onNodes = {}, last = end(), leaf = last && data.leaves[last];
    path.forEach(function (id) { onChips[id] = true; onNodes[data.chips[id].node] = true; });
    if (last && !leaf) onNodes[last] = true;
    tree.classList.toggle("has-path", path.length > 0);
    tree.dataset.tone = leaf ? leaf.tone : "";

    tree.querySelectorAll("[data-chip]").forEach(function (b) {
      var id = b.dataset.chip, c = data.chips[id];
      b.classList.toggle("is-on", !!onChips[id]);
      b.classList.toggle("is-option", !!last && !leaf && c.node === last);
      b.setAttribute("aria-pressed", onChips[id] ? "true" : "false");
    });
    tree.querySelectorAll("[data-node]").forEach(function (n) {
      n.classList.toggle("is-on", !!onNodes[n.dataset.node]);
      n.classList.remove("is-next");
    });
    if (last && !leaf) {
      var next = q('[data-node="' + last + '"]');
      void next.offsetWidth; // restart the one-off ring on the next question
      next.classList.add("is-next");
    }
    tree.querySelectorAll("[data-leaf]").forEach(function (l) { l.classList.toggle("is-on", l.dataset.leaf === last); });

    var nowLit = {};
    svg.querySelectorAll(".hiw-link").forEach(function (p) {
      var i = path.indexOf(p.dataset.link), key = p.dataset.link + p.dataset.part, on = i >= 0;
      p.classList.toggle("is-on", on);
      if (on) nowLit[key] = true;
      p.classList.remove("is-drawing");
      if (on && animate && !lit[key] && !reduceMotion) {
        p.style.setProperty("--d", (i * 2 + (p.dataset.part === "out" ? 1 : 0)) * 90 + "ms");
        void p.getBoundingClientRect();
        p.classList.add("is-drawing");
      }
    });
    // keep path links above the others
    Array.prototype.forEach.call(svg.querySelectorAll(".hiw-link.is-on"), function (p) { svg.appendChild(p); });
    lit = nowLit;

    root.querySelectorAll("[data-preset]").forEach(function (b) {
      b.setAttribute("aria-pressed", path.length && b.dataset.preset === path[path.length - 1] ? "true" : "false");
    });
    renderReadout(last, leaf);
    renderStepper();
  }

  function select(id, animate) {
    path = data.chips[id].path.slice();
    paint(animate !== false);
  }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }

  // ---------------------------------------------------------------- readout (also the live announcement)
  function pill(leaf) {
    return '<span class="outcome-pill tone-' + leaf.tone + '">' + data.icons[{ go: "circle-check", stop: "ban", ask: "help-circle", neutral: "circle-minus" }[leaf.tone]] +
      "<span>" + esc(leaf.label) + "</span></span>";
  }
  function renderReadout(last, leaf) {
    if (!path.length) { readout.innerHTML = '<span class="hiw-hint">Choose an answer in the tree to trace its path.</span>'; return; }
    var crumbs = path.map(function (id) {
      var c = data.chips[id];
      return '<span class="crumb"><span class="sr-only">' + esc(data.nodes[c.node].title) + ": </span>" + esc(c.label) + "</span>";
    }).join(data.icons["arrow-right"]);
    var tail = leaf ? pill(leaf)
                    : '<span class="hiw-next">Next: ' + esc(data.nodes[last].title) + "</span>";
    readout.innerHTML = '<span class="hiw-crumbs">' + crumbs + "</span>" + data.icons["arrow-right"] + tail;
  }

  // ---------------------------------------------------------------- phone stepper (same choices, one at a time)
  function renderStepper() {
    var active = document.activeElement, focusId = active && stepper.contains(active) ? active.dataset.chip : null;
    var html = "", nodeId = data.root, n = 0;
    while (nodeId) {
      var node = data.nodes[nodeId], chosen = null;
      path.forEach(function (id) { if (data.chips[id].node === nodeId) chosen = id; });
      n++;
      var opts = node.chips;
      html += '<li class="stp-step ' + (chosen ? "is-done" : "is-now") + '"' + (chosen ? "" : ' aria-current="step"') + ">" +
        '<div class="stp-head tip-host"><span class="stp-dot" aria-hidden="true">' + (chosen ? data.icons.check : n) + "</span>" +
        '<h3 class="stp-title" id="stp-' + nodeId + '">' + esc(node.title) + "</h3>" +
        '<button type="button" class="info" aria-label="About: ' + esc(node.title) + '" aria-describedby="stp-tip-' + nodeId + '">' + data.icons["info-circle"] + "</button>" +
        '<span class="tip" role="tooltip" id="stp-tip-' + nodeId + '">' + esc(node.info) + "</span></div>" +
        '<div class="stp-opts" role="group" aria-labelledby="stp-' + nodeId + '">' +
        opts.map(function (id) {
          var on = id === chosen;
          return '<button type="button" class="hiw-chip stp-opt' + (on ? " is-on" : "") + '" data-chip="' + id + '" aria-pressed="' + on + '">' + esc(data.chips[id].label) + "</button>";
        }).join("") + "</div></li>";
      if (!chosen) break;
      var to = data.chips[chosen].to;
      if (data.leaves[to]) {
        var leaf = data.leaves[to];
        html += '<li class="stp-out"><div class="outcome tone-' + leaf.tone + '"><p class="outcome-label">' +
          data.icons[{ go: "circle-check", stop: "ban", ask: "help-circle", neutral: "circle-minus" }[leaf.tone]] + "<span>" + esc(leaf.label) + "</span></p>" +
          '<p class="hiw-tags">' + leaf.tags.map(function (t) { return '<span class="hiw-tag" title="' + esc(t.detail) + '">' + esc(t.tag) + "</span>"; }).join("") + "</p>" +
          '<p class="stp-why">' + esc(leaf.why) + "</p></div></li>";
        break;
      }
      nodeId = to;
    }
    stepper.innerHTML = '<ol class="stp">' + html + "</ol>";
    if (focusId) {
      var again = stepper.querySelector('[data-chip="' + focusId + '"]');
      if (again) again.focus();
    }
    if (stepper.offsetParent && path.length) {
      var lastStep = stepper.querySelector(".stp-out, .stp-step:last-child");
      var r = lastStep.getBoundingClientRect();
      if (r.bottom > window.innerHeight) lastStep.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    }
  }

  // ---------------------------------------------------------------- events
  root.addEventListener("click", function (e) {
    var chip = e.target.closest("[data-chip]");
    if (chip) { clearTimers(); select(chip.dataset.chip); return; }
    var preset = e.target.closest("[data-preset]");
    if (preset) {
      clearTimers();
      var full = data.chips[preset.dataset.preset].path;
      if (reduceMotion) { select(preset.dataset.preset, false); return; }
      path = [];
      paint(false);
      full.forEach(function (id, i) { timers.push(setTimeout(function () { select(id); }, 120 + i * 520)); });
      return;
    }
    if (e.target.closest("[data-reset]")) { clearTimers(); path = []; paint(false); }
  });

  if (window.ResizeObserver) new ResizeObserver(function () { draw(); }).observe(tree);
  else window.addEventListener("resize", draw);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
  draw();
  renderStepper();
})();
