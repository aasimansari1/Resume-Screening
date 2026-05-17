/* ==========================================================
   AI Resume Screener — Main JavaScript
   ========================================================== */

document.addEventListener('DOMContentLoaded', function () {

  // -------------------------------------------------------
  // Sidebar toggle
  // -------------------------------------------------------
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('main-content');
  const sidebarToggle = document.getElementById('sidebarToggle');

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      if (window.innerWidth < 992) {
        sidebar.classList.toggle('open');
      } else {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
      }
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function (e) {
      if (window.innerWidth < 992 &&
          sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // -------------------------------------------------------
  // Dark mode toggle
  // -------------------------------------------------------
  const themeToggle = document.getElementById('themeToggle');
  const html = document.documentElement;
  const savedTheme = localStorage.getItem('theme') || 'light';

  function applyTheme(theme) {
    html.setAttribute('data-bs-theme', theme);
    localStorage.setItem('theme', theme);
    if (themeToggle) {
      themeToggle.querySelector('i').className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
  }

  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const current = html.getAttribute('data-bs-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  // -------------------------------------------------------
  // Auto-dismiss flash alerts
  // -------------------------------------------------------
  document.querySelectorAll('.alert').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert && bsAlert.close();
    }, 6000);
  });

  // -------------------------------------------------------
  // Animate KPI cards on load
  // -------------------------------------------------------
  const kpiCards = document.querySelectorAll('.kpi-card');
  kpiCards.forEach(function (card, i) {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    setTimeout(function () {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 100 + i * 80);
  });

  // -------------------------------------------------------
  // Progress bar animations
  // -------------------------------------------------------
  const progressBars = document.querySelectorAll('.progress-bar');
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const bar = entry.target;
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(function () {
          bar.style.transition = 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
          bar.style.width = width;
        }, 100);
        observer.unobserve(bar);
      }
    });
  }, { threshold: 0.2 });

  progressBars.forEach(function (bar) {
    observer.observe(bar);
  });

  // -------------------------------------------------------
  // Tooltip initialization
  // -------------------------------------------------------
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // -------------------------------------------------------
  // Candidate table — highlight on hover
  // -------------------------------------------------------
  document.querySelectorAll('.candidate-row').forEach(function (row) {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function (e) {
      if (!e.target.closest('a, button')) {
        const id = this.dataset.id;
        if (id) window.location.href = `/candidate/${id}`;
      }
    });
  });

  // -------------------------------------------------------
  // Copy to clipboard for email
  // -------------------------------------------------------
  document.querySelectorAll('[data-copy]').forEach(function (el) {
    el.addEventListener('click', function () {
      navigator.clipboard.writeText(this.dataset.copy).then(function () {
        showToast('Copied to clipboard!', 'success');
      });
    });
  });

});

// -------------------------------------------------------
// Toast helper
// -------------------------------------------------------
function showToast(message, type = 'info') {
  const container = getOrCreateToastContainer();
  const id = 'toast-' + Date.now();
  const icons = { success: 'check-circle', danger: 'exclamation-triangle', info: 'info-circle', warning: 'exclamation-circle' };
  const icon = icons[type] || 'info-circle';

  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive">
      <div class="d-flex">
        <div class="toast-body">
          <i class="fas fa-${icon} me-2"></i>${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;

  container.insertAdjacentHTML('beforeend', html);
  const toastEl = document.getElementById(id);
  const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

function getOrCreateToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
  }
  return container;
}

// -------------------------------------------------------
// Format numbers with commas
// -------------------------------------------------------
function formatNumber(n) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// -------------------------------------------------------
// Animate count-up for KPI values
// -------------------------------------------------------
function animateCount(el, target, duration = 1000) {
  let start = 0;
  const increment = target / (duration / 16);
  const isFloat = target % 1 !== 0;

  const timer = setInterval(function () {
    start += increment;
    if (start >= target) {
      clearInterval(timer);
      start = target;
    }
    el.textContent = isFloat ? start.toFixed(1) : Math.floor(start);
  }, 16);
}

// Run count-up on KPI values
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.kpi-value').forEach(function (el) {
    const raw = parseFloat(el.textContent.replace('%', '').replace(',', ''));
    if (!isNaN(raw) && raw > 0) {
      el.textContent = '0';
      setTimeout(() => animateCount(el, raw), 300);
    }
  });
});
