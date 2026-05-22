// YolPayı Main JS
document.addEventListener('DOMContentLoaded', () => {
  const toggler = document.querySelector('.navbar-toggler');
  const nav = document.querySelector('.navbar-nav');
  const sidebarToggler = document.querySelector('.sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggler && nav) toggler.addEventListener('click', () => nav.classList.toggle('open'));
  if (sidebarToggler && sidebar) sidebarToggler.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => { alert.style.transition = 'opacity 0.5s'; alert.style.opacity = '0'; setTimeout(() => alert.remove(), 500); }, 4000);
  });
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target);
    let current = 0;
    const step = Math.ceil(target / 50);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current.toLocaleString("tr-TR");
      if (current >= target) clearInterval(timer);
    }, 30);
  });
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => { if (!confirm(btn.dataset.confirm)) e.preventDefault(); });
  });
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('animate-in'); observer.unobserve(e.target); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.feature-card, .trip-card, .stat-card').forEach(el => observer.observe(el));
  document.querySelectorAll('.notif-item[data-id]').forEach(item => {
    item.addEventListener('click', () => {
      fetch(`/api/notifications/read/${item.dataset.id}`, { method: 'POST' }).then(() => item.classList.remove('unread'));
    });
  });
});
function openModal(id) { document.getElementById(id)?.classList.add('active'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('active'); }
document.addEventListener('click', e => { if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('active'); });
