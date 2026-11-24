// GxP AI Use-Case Assistant: progressive enhancement only. Every page also works without JavaScript
// (the server validates the form and re-renders it with inline errors).
(function () {
  "use strict";

  // ------------------------------------------------------------ (i) tooltips
  // Shown on hover and keyboard focus by CSS; click/tap toggles them (touch); Escape dismisses.
  // A tooltip lives in an option card (.opt) or in any other positioned box marked .tip-host (/how-it-works).
  var HOST = ".opt, .tip-host";
  function placeTip(opt) {
    var tip = opt.querySelector(".tip");
    if (!tip) return;
    tip.style.setProperty("--shift", "0px");
    var r = tip.getBoundingClientRect();
    var vw = document.documentElement.clientWidth;
    var shift = 0;
    if (r.left < 16) shift = 16 - r.left;
    else if (r.right > vw - 16) shift = vw - 16 - r.right;
    tip.style.setProperty("--shift", shift + "px");
  }
  function closeTips(except) {
    document.querySelectorAll(".opt.tip-open, .tip-host.tip-open").forEach(function (o) {
      if (o !== except) o.classList.remove("tip-open");
    });
  }
  document.addEventListener("pointerover", function (e) {
    var btn = e.target.closest && e.target.closest(".info");
    if (btn) { var opt = btn.closest(HOST); opt.classList.remove("tip-dismissed"); placeTip(opt); }
  });
  document.addEventListener("pointerout", function (e) {
    var opt = e.target.closest && e.target.closest(HOST);
    if (opt && !opt.contains(e.relatedTarget)) opt.classList.remove("tip-dismissed");
  });
  document.addEventListener("focusin", function (e) {
    var btn = e.target.closest && e.target.closest(".info");
    if (btn) { var opt = btn.closest(HOST); opt.classList.remove("tip-dismissed"); placeTip(opt); }
  });
  document.addEventListener("focusout", function (e) {
    var btn = e.target.closest && e.target.closest(".info");
    if (btn) btn.closest(HOST).classList.remove("tip-open", "tip-dismissed");
  });
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".info");
    if (btn) {
      var opt = btn.closest(HOST);
      closeTips(opt);
      opt.classList.remove("tip-dismissed");
      opt.classList.toggle("tip-open");
      placeTip(opt);
      return;
    }
    if (!(e.target.closest && e.target.closest(".tip"))) closeTips(null);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var shown = document.querySelectorAll(".opt.tip-open, .opt:hover, .opt:focus-within, .tip-host.tip-open, .tip-host:hover, .tip-host:focus-within");
    shown.forEach(function (o) { o.classList.remove("tip-open"); o.classList.add("tip-dismissed"); });
  });

  // ------------------------------------------------------------ busy state and progress on submit
  // The request is a normal form POST (full page load), so nothing reports real progress. The display is
  // honest about that (W52): an immediate confirmation, a bar that follows elapsed time and eases toward
  // 90 % without ever finishing, the pipeline steps in their real order with only the classifier step
  // (the one that takes time) shown as current, and a calm note after 30 s. Screen readers hear the start
  // and the 30 s note only. The new page replaces all of this; an error comes back as a re-rendered form.
  var PROGRESS = { tau: 7000, cap: 90, classifyAt: 1200, slowNoteAt: 30000, keywordRevealAt: 900, tick: 250 };
  var timers = [];
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function showProgress(form, slow, status) {
    var box = form.querySelector("[data-progress]");
    if (!box) return;
    var fill = box.querySelector("[data-progress-fill]"), bar = box.querySelector("[data-progress-bar]");
    var time = box.querySelector("[data-progress-time]"), note = box.querySelector("[data-progress-slow]");
    var steps = box.querySelectorAll("[data-step]"), classify = box.querySelector("[data-step-classify]");
    var start = Date.now(), current = -1;
    if (classify) classify.textContent = slow ? classify.dataset.ai : classify.dataset.keyword;
    box.querySelector("[data-progress-title]").textContent = form.querySelector("textarea[name=description]") && !form.querySelector("[data-q]")
      ? "Your description was sent for screening." : "Your answers were sent for screening.";
    function setStep(i) {
      if (i === current) return;
      current = i;
      steps.forEach(function (s, k) {
        s.classList.toggle("is-done", k < i);
        s.classList.toggle("is-now", k === i);
        if (k === i) s.setAttribute("aria-current", "step"); else s.removeAttribute("aria-current");
      });
      bar.setAttribute("aria-valuetext", "Step " + (i + 1) + " of " + steps.length + ": " + steps[i].textContent.trim());
    }
    function frame() {
      var t = Date.now() - start;
      var p = PROGRESS.cap * (1 - Math.exp(-t / PROGRESS.tau));
      fill.style.transform = "scaleX(" + (p / 100).toFixed(4) + ")";
      bar.setAttribute("aria-valuenow", String(Math.round(p)));
      var s = Math.floor(t / 1000);
      time.textContent = s >= 1 ? s + " s" : "";
      setStep(t < PROGRESS.classifyAt ? 0 : 1);
      if (t >= PROGRESS.slowNoteAt && note.hidden) {
        note.hidden = false;
        if (status) status.textContent = "This is taking longer than usual. Your answers are safe. Keep this page open.";
      }
    }
    box.hidden = false;
    box.classList.toggle("is-calm", reduceMotion);
    frame();
    // Reduced motion: the bar still moves (it carries information) but in coarse steps without a transition.
    timers.push(setInterval(frame, reduceMotion ? 1000 : PROGRESS.tick));
    if (box.getBoundingClientRect().bottom > window.innerHeight) box.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
  }
  function resetProgress() {
    timers.forEach(function (id) { clearInterval(id); clearTimeout(id); });
    timers = [];
    document.querySelectorAll("[data-progress]").forEach(function (box) {
      box.hidden = true;
      box.querySelector("[data-progress-slow]").hidden = true;
      box.querySelector("[data-progress-fill]").style.transform = "";
      box.querySelector("[data-progress-time]").textContent = "";
      var bar = box.querySelector("[data-progress-bar]");
      bar.setAttribute("aria-valuenow", "0");
      bar.removeAttribute("aria-valuetext");
      box.querySelectorAll("[data-step]").forEach(function (s) { s.classList.remove("is-done", "is-now"); s.removeAttribute("aria-current"); });
    });
  }

  function setBusy(form, submitter) {
    var btn = submitter || form.querySelector("button[type=submit]");
    var status = form.querySelector("[data-status]");
    var provider = form.querySelector("select[name=provider]");
    // Slow: an AI classifier was chosen in the selector, on a "screen again" button, or (follow-up form) on the form itself.
    var slow = provider ? !!provider.selectedOptions[0].hasAttribute("data-slow")
                        : form.hasAttribute("data-slow") || !!(submitter && submitter.value && submitter.value !== "offline");
    form.dataset.submitting = "1";
    form.setAttribute("aria-busy", "true");
    if (status) {
      status.textContent = slow ? "Your answers were sent. Screening with an AI classifier, usually 5 to 15 seconds."
                                : "Your answers were sent. Screening the use case.";
    }
    // An AI classifier: show the progress at once. The keyword baseline usually answers in well under a
    // second, so its progress appears only if the page has not loaded yet (no flash for a near-instant reply).
    if (slow) showProgress(form, true, status);
    else timers.push(setTimeout(function () { showProgress(form, false, status); }, PROGRESS.keywordRevealAt));
    // Disable after the browser has collected the form data, so the submitter's name/value is still sent.
    setTimeout(function () {
      form.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = true; });
      if (btn) {
        btn.classList.add("is-busy");
        var label = btn.querySelector(".btn-label");
        if (label && btn.dataset.busyLabel) { btn.dataset.idleLabel = label.textContent; label.textContent = btn.dataset.busyLabel; }
      }
    }, 0);
  }
  function resetBusy() {
    resetProgress();
    document.querySelectorAll("form[data-busy]").forEach(function (form) {
      delete form.dataset.submitting;
      form.removeAttribute("aria-busy");
      var status = form.querySelector("[data-status]");
      if (status) status.textContent = "";
      form.querySelectorAll("button[type=submit]").forEach(function (b) {
        b.disabled = false;
        b.classList.remove("is-busy");
        var label = b.querySelector(".btn-label");
        if (label && b.dataset.idleLabel) label.textContent = b.dataset.idleLabel;
      });
    });
  }
  window.addEventListener("pageshow", function (e) { if (e.persisted) resetBusy(); });

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches("form[data-busy]")) return;
    if (form.dataset.submitting) { e.preventDefault(); return; }
    if (form.id === "intake" && !validateWhat(true)) { e.preventDefault(); return; }
    if (form.id !== "intake" && form.querySelector("textarea[required]") && !form.checkValidity()) {
      e.preventDefault(); form.reportValidity(); return;
    }
    setBusy(form, e.submitter);
  });

  // ------------------------------------------------------------ landing: rotating example cards (W52)
  // Three examples share one grid cell, so the card area keeps the height of the tallest one (no layout
  // shift). Rotation every ~5.5 s; it pauses while the pointer is over the card or the tab is hidden, and
  // stops for good once keyboard focus enters or a dot is chosen (WAI carousel pattern), until "Play".
  // With reduced motion there is no automatic rotation: the dots switch cards without animation.
  (function deck() {
    var root = document.querySelector("[data-deck]");
    if (!root) return;
    var fig = root.closest("figure");
    var cards = root.querySelectorAll("[data-card]"), live = root.querySelector("[data-deck-cards]");
    var controls = fig.querySelector("[data-deck-controls]"), dots = fig.querySelectorAll("[data-deck-go]");
    var toggle = fig.querySelector("[data-deck-toggle]");
    var INTERVAL = 5500, index = 0, timer = null, hover = false;
    var playing = !reduceMotion;
    controls.hidden = false;
    if (reduceMotion) toggle.hidden = true;

    function show(i, byUser) {
      var prev = index;
      index = (i + cards.length) % cards.length;
      if (index === prev) return;
      cards.forEach(function (c, k) {
        c.classList.toggle("is-active", k === index);
        c.classList.toggle("is-leaving", k === prev);
        if (k === index) c.removeAttribute("aria-hidden"); else c.setAttribute("aria-hidden", "true");
      });
      dots.forEach(function (d, k) { if (k === index) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
      // Announce the new card only when the person chose it, never on automatic rotation.
      live.setAttribute("aria-live", byUser ? "polite" : "off");
    }
    function schedule() {
      clearTimeout(timer);
      if (playing && !hover && !document.hidden) timer = setTimeout(function () { show(index + 1, false); schedule(); }, INTERVAL);
    }
    function setPlaying(on) {
      playing = on;
      toggle.textContent = on ? "Pause" : "Play";
      toggle.setAttribute("aria-label", on ? "Stop rotating examples" : "Start rotating examples");
      schedule();
    }
    dots.forEach(function (d) {
      d.addEventListener("click", function () { show(parseInt(d.dataset.deckGo, 10), true); setPlaying(false); });
    });
    toggle.addEventListener("click", function () { setPlaying(!playing); if (playing) show(index + 1, false); });
    root.addEventListener("pointerenter", function () { hover = true; schedule(); });
    root.addEventListener("pointerleave", function () { hover = false; schedule(); });
    // Keyboard focus on the controls stops rotation; the toggle itself is exempt so it can restart it.
    fig.addEventListener("focusin", function (e) { if (e.target !== toggle && playing) setPlaying(false); });
    document.addEventListener("visibilitychange", schedule);
    setPlaying(playing);
  })();

  // ------------------------------------------------------------ quick mode examples
  document.querySelectorAll("[data-fill]").forEach(function (b) {
    b.addEventListener("click", function () {
      var t = document.getElementById(b.dataset.fill);
      t.value = b.textContent.trim();
      t.focus();
    });
  });

  // ------------------------------------------------------------ intake form
  var form = document.getElementById("intake");
  if (!form) return;
  var what = form.querySelector("textarea[data-min]");
  var whatError = what && document.getElementById(what.id + "-error");

  function showError(msg) {
    whatError.querySelector("[data-msg]").textContent = msg;
    whatError.hidden = false;
    what.setAttribute("aria-invalid", "true");
  }
  function clearError() {
    if (!whatError) return;
    whatError.hidden = true;
    whatError.querySelector("[data-msg]").textContent = "";
    what.removeAttribute("aria-invalid");
  }
  function validateWhat(onSubmit) {
    if (!what) return true;
    var n = what.value.trim().length, min = parseInt(what.dataset.min, 10);
    if (n >= min) { clearError(); return true; }
    if (!onSubmit && n === 0) return true; // do not nag while the field is still empty
    showError(n === 0 ? "Please describe what the AI should do (at least " + min + " characters)."
                      : "Please write at least " + min + " characters (" + n + " so far).");
    if (onSubmit) { what.closest("details").open = true; what.focus(); }
    return false;
  }
  if (what) {
    what.addEventListener("blur", function () { validateWhat(false); });
    what.addEventListener("input", function () { if (what.getAttribute("aria-invalid")) validateWhat(false); });
  }
  // answered counters
  function answered(q) {
    var type = q.dataset.type;
    if (type === "text" || type === "textarea") return q.querySelector("input, textarea").value.trim() !== "";
    if (type === "multi") return !!q.querySelector("input:checked");
    var ex = q.querySelector("textarea");
    return !!q.querySelector("input[type=radio]:checked") || (ex ? ex.value.trim() !== "" : false);
  }
  var total = form.querySelector("[data-total]");
  function updateCounts(updateTotal) {
    var all = 0, done = 0;
    form.querySelectorAll("[data-section]").forEach(function (s) {
      var qs = s.querySelectorAll("[data-q]"), n = 0;
      qs.forEach(function (q) { if (answered(q)) n++; });
      s.querySelector("[data-count]").textContent = n + " of " + qs.length + " answered";
      all += qs.length; done += n;
    });
    if (updateTotal && total) total.textContent = done + " of " + all + " questions answered";
  }
  form.addEventListener("input", function () { updateCounts(false); });
  form.addEventListener("change", function () { updateCounts(true); });

  // example prefill and clear
  var examples = JSON.parse(document.getElementById("examples-data").textContent);
  var exStatus = document.getElementById("examples-status");
  function fill(data) {
    form.querySelectorAll("[data-q]").forEach(function (q) {
      var id = q.dataset.q, type = q.dataset.type, v = data[id];
      if (type === "text" || type === "textarea") {
        q.querySelector("input, textarea").value = v || "";
      } else if (type === "multi") {
        q.querySelectorAll("input[type=checkbox]").forEach(function (c) { c.checked = (v || []).indexOf(c.value) >= 0; });
      } else {
        var choice = v && v.choice;
        q.querySelectorAll("input[type=radio]").forEach(function (r) { r.checked = r.value === choice; });
        var ex = q.querySelector("textarea");
        if (ex) ex.value = (v && v.explain) || "";
      }
    });
    // Follow-up answers belong to the case being replaced, so an example or "Clear form" empties them too
    // (an empty answer is left out by the server). The round itself is kept: "Start a new use case" leaves it.
    form.querySelectorAll("textarea[data-fu-answer]").forEach(function (t) { t.value = ""; });
    clearError();
    form.querySelectorAll("details[data-section]").forEach(function (d) { d.open = true; });
    updateCounts(true);
  }
  function hasAnswers() {
    return Array.prototype.some.call(form.querySelectorAll("[data-q]"), answered) ||
      Array.prototype.some.call(form.querySelectorAll("textarea[data-fu-answer]"), function (t) { return t.value.trim() !== ""; });
  }
  document.querySelectorAll("[data-example]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (hasAnswers() && !window.confirm("Replace your current answers with this example?")) return;
      var ex = examples[parseInt(b.dataset.example, 10)];
      fill(ex.form);
      exStatus.textContent = "Example filled in: " + ex.name + ". Check the answers, then screen the use case.";
    });
  });
  var clearBtn = document.querySelector("[data-clear]");
  if (clearBtn) clearBtn.addEventListener("click", function () {
    if (hasAnswers() && !window.confirm("Clear all answers?")) return;
    fill({});
    exStatus.textContent = "Form cleared.";
    var first = form.querySelector("input[type=text], textarea");
    if (first) first.focus();
  });

  // after a server-side error, move focus to the field or the alert
  var invalid = form.querySelector("[aria-invalid=true]");
  if (invalid) { invalid.closest("details").open = true; invalid.focus(); }
  else { var alertBox = document.getElementById("form-alert"); if (alertBox) { alertBox.tabIndex = -1; alertBox.focus(); } }
})();
