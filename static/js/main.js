// CwHUB CFG - global JS (barcha sahifalarda ulanadi)

document.addEventListener("DOMContentLoaded", () => {
  // Mobile navbar toggle
  const toggleBtn = document.querySelector(".nav-toggle");
  const navLinks = document.querySelector(".nav-links");
  if (toggleBtn && navLinks) {
    toggleBtn.addEventListener("click", () => {
      navLinks.classList.toggle("open");
    });
  }

  // Flash xabarlarni bir necha soniyadan keyin avtomatik yashirish
  document.querySelectorAll(".alert").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // Fayl inputlar uchun tanlangan fayl nomini ko'rsatish
  document.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener("change", () => {
      const label = input.closest(".form-group")?.querySelector(".file-name-preview");
      if (label && input.files.length) {
        label.textContent = input.files[0].name;
      }
    });
  });
});

// Tasdiqlash talab qilinadigan formalar uchun (masalan o'chirish)
function confirmSubmit(form, message) {
  if (confirm(message || "Ishonchingiz komilmi?")) {
    form.submit();
  }
  return false;
}
