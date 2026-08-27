/* =========================================================
   MAIN.JS — Hamdaan CMS public site interactions
   (Content itself is server-rendered from the database;
   this file only handles client-side UI behaviour.)
   ========================================================= */

const THEME_KEY = 'hic_theme';

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initStickyNav();
  initMobileMenu();
  initRevealOnScroll();
  initCounters();
  initGalleryLightbox();
  initFormFieldClearOnInput();
  autoDismissMessages();
});

/* ---------- Dark mode ---------- */
function initThemeToggle() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  document.querySelectorAll('[data-theme-toggle]').forEach(btn => {
    updateThemeIcon(btn);
    btn.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem(THEME_KEY, 'light'); }
      else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem(THEME_KEY, 'dark'); }
      document.querySelectorAll('[data-theme-toggle]').forEach(updateThemeIcon);
    });
  });
}
function updateThemeIcon(btn) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const icon = btn.querySelector('i');
  if (icon) icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
}

/* ---------- Sticky navbar ---------- */
function initStickyNav() {
  const nav = document.getElementById('mainNavbar');
  if (!nav) return;
  window.addEventListener('scroll', () => nav.classList.toggle('scrolled', window.scrollY > 12));
}

/* ---------- Mobile menu drawer ---------- */
function initMobileMenu() {
  const btn = document.getElementById('hamburgerBtn');
  const menu = document.getElementById('mobileMenu');
  const overlay = document.getElementById('mobileOverlay');
  const closeBtn = document.getElementById('mobileMenuClose');
  if (!btn || !menu) return;
  const open = () => { btn.classList.add('open'); menu.classList.add('open'); overlay.classList.add('open'); document.body.style.overflow = 'hidden'; };
  const close = () => { btn.classList.remove('open'); menu.classList.remove('open'); overlay.classList.remove('open'); document.body.style.overflow = ''; };
  btn.addEventListener('click', () => menu.classList.contains('open') ? close() : open());
  closeBtn?.addEventListener('click', close);
  overlay?.addEventListener('click', close);
}

/* ---------- Reveal on scroll ---------- */
function initRevealOnScroll() {
  const items = document.querySelectorAll('.reveal');
  if (!items.length) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('in-view'); observer.unobserve(entry.target); }
    });
  }, { threshold: 0.15 });
  items.forEach(item => observer.observe(item));
}

/* ---------- Animated counters ---------- */
function initCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseFloat(el.getAttribute('data-count'));
      const suffix = el.getAttribute('data-suffix') || '';
      const duration = 1400;
      const start = performance.now();
      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;
        el.textContent = (Number.isInteger(target) ? Math.floor(value).toLocaleString() : value.toFixed(1)) + suffix;
        if (progress < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      observer.unobserve(el);
    });
  }, { threshold: 0.4 });
  counters.forEach(c => observer.observe(c));
}

/* ---------- Gallery lightbox ---------- */
function initGalleryLightbox() {
  const items = Array.from(document.querySelectorAll('.gallery-item[data-lightbox]'));
  const lightbox = document.getElementById('galleryLightbox');
  if (!items.length || !lightbox) return;
  let index = 0;
  const img = document.getElementById('lightboxImg');
  const caption = document.getElementById('lightboxCaption');

  const update = () => {
    const el = items[index];
    img.src = el.dataset.image;
    caption.textContent = el.dataset.caption || '';
  };
  items.forEach((el, i) => el.addEventListener('click', () => {
    index = i; update(); lightbox.classList.add('open');
  }));
  document.getElementById('lightboxClose')?.addEventListener('click', () => lightbox.classList.remove('open'));
  document.getElementById('lightboxPrev')?.addEventListener('click', () => { index = (index - 1 + items.length) % items.length; update(); });
  document.getElementById('lightboxNext')?.addEventListener('click', () => { index = (index + 1) % items.length; update(); });
  lightbox.addEventListener('click', e => { if (e.target === lightbox) lightbox.classList.remove('open'); });
  document.addEventListener('keydown', e => {
    if (!lightbox.classList.contains('open')) return;
    if (e.key === 'Escape') lightbox.classList.remove('open');
    if (e.key === 'ArrowLeft') document.getElementById('lightboxPrev')?.click();
    if (e.key === 'ArrowRight') document.getElementById('lightboxNext')?.click();
  });
}

/* ---------- Clear field error styling once the user edits it ---------- */
function initFormFieldClearOnInput() {
  document.querySelectorAll('.field.error input, .field.error select, .field.error textarea').forEach(input => {
    input.addEventListener('input', () => input.closest('.field')?.classList.remove('error'), { once: true });
  });
}

/* ---------- Password visibility toggle (kept for parity / future portal use) ---------- */
function initPasswordToggle() {
  document.querySelectorAll('.pass-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.parentElement.querySelector('input');
      if (!input) return;
      const isPass = input.type === 'password';
      input.type = isPass ? 'text' : 'password';
      btn.innerHTML = isPass ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
    });
  });
}

/* ---------- Auto-dismiss Django messages rendered as toasts ---------- */
function autoDismissMessages() {
  document.querySelectorAll('.toast-container .toast').forEach(toast => {
    const remove = () => { toast.style.animation = 'slideInRight .25s ease reverse'; setTimeout(() => toast.remove(), 200); };
    toast.querySelector('.toast-close')?.addEventListener('click', remove);
    setTimeout(remove, 6000);
  });
}
