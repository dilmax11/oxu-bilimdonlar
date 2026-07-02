// Bilimdonlar — umumiy JS
// O'chirish/holatini o'zgartirish kabi "xavfli" amallar uchun tasdiqlash oynasi.

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const message = form.getAttribute("data-confirm");
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // Flash xabarlarini bir necha soniyadan keyin asta yo'qotish
  document.querySelectorAll(".alert[data-autohide]").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.5s ease";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 500);
    }, 4000);
  });
});
