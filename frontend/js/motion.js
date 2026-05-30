/**
 * GiveFund UI motion — scroll reveal, stat counters, nav glass (vanilla).
 */
(function () {
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function initNavScroll() {
    const nav = document.querySelector(".nav");
    if (!nav) return;
    const onScroll = () => {
      nav.classList.toggle("is-scrolled", window.scrollY > 24);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function initReveal() {
    const nodes = document.querySelectorAll("[data-reveal]");
    if (!nodes.length) return;

    if (prefersReduced) {
      nodes.forEach((el) => el.classList.add("is-visible"));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    nodes.forEach((el) => io.observe(el));
  }

  function animateCounter(el, target, duration) {
    const start = performance.now();
    const from = 0;
    const isFloat = target % 1 !== 0;

    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const val = from + (target - from) * eased;
      if (isFloat) {
        el.textContent = val >= 1e6
          ? `$${(val / 1e6).toFixed(1)}M`
          : val >= 1e3
            ? `$${Math.round(val).toLocaleString()}`
            : Math.round(val).toLocaleString();
      } else {
        el.textContent = Math.round(val).toLocaleString();
      }
      if (t < 1) requestAnimationFrame(frame);
      else el.classList.remove("counting");
    }
    el.classList.add("counting");
    requestAnimationFrame(frame);
  }

  function initMetricCounters() {
    document.querySelectorAll(".metric[data-metric]").forEach((metric) => {
      if (metric.dataset.counted === "1") return;
      const valueEl = metric.querySelector(".metric-value");
      const raw = metric.dataset.metric;
      if (!valueEl || raw === undefined || raw === "" || raw === "—") return;
      metric.dataset.counted = "1";

      const num = parseFloat(raw);
      if (Number.isNaN(num)) return;

      if (prefersReduced) {
        valueEl.textContent = metric.dataset.display || valueEl.textContent;
        return;
      }

      const io = new IntersectionObserver(
        (entries) => {
          if (!entries[0].isIntersecting) return;
          io.disconnect();
          metric.classList.add("is-visible");
          valueEl.textContent = "0";
          animateCounter(valueEl, num, 1400);
          if (metric.dataset.display) {
            setTimeout(() => {
              valueEl.textContent = metric.dataset.display;
            }, 1450);
          }
        },
        { threshold: 0.4 }
      );
      io.observe(metric);
    });
  }

  function initFeedStagger() {
    const feed = document.getElementById("campaignGrid");
    if (!feed || prefersReduced) return;

    const observer = new MutationObserver(() => {
      feed.querySelectorAll(".signal-card:not([data-reveal])").forEach((card, i) => {
        card.setAttribute("data-reveal", "");
        card.style.setProperty("--stagger", String(i % 12));
      });
      initReveal();
    });
    observer.observe(feed, { childList: true });
  }

  function initHeroParallax() {
    if (prefersReduced) return;
    const aurora = document.querySelector(".hero-aurora");
    if (!aurora) return;
    window.addEventListener(
      "mousemove",
      (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 12;
        const y = (e.clientY / window.innerHeight - 0.5) * 8;
        aurora.style.transform = `translate(${x}px, ${y}px)`;
      },
      { passive: true }
    );
  }

  function boot() {
    initNavScroll();
    initReveal();
    initMetricCounters();
    initFeedStagger();
    initHeroParallax();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.GiveFundMotion = { initReveal, initMetricCounters };
})();
