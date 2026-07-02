// Bilimdonlar — test ichidagi sanoq (countdown) taymer
// take_test.html sahifasida ishlatiladi.
// HTML elementlari: #timer-box, #timer-digits, #test-form

(function () {
  const timerBox = document.getElementById("timer-box");
  const digits = document.getElementById("timer-digits");
  const form = document.getElementById("test-form");

  if (!timerBox || !digits || !form) return;

  let remaining = parseInt(timerBox.getAttribute("data-remaining"), 10) || 0;
  let submitted = false;

  function format(total) {
    const m = Math.floor(total / 60).toString().padStart(2, "0");
    const s = (total % 60).toString().padStart(2, "0");
    return m + ":" + s;
  }

  function tick() {
    if (submitted) return;

    digits.textContent = format(Math.max(remaining, 0));

    if (remaining <= 60) {
      timerBox.classList.add("timer-warning");
    }

    if (remaining <= 0) {
      submitted = true;
      digits.textContent = "00:00";
      form.submit();
      return;
    }

    remaining -= 1;
    setTimeout(tick, 1000);
  }

  tick();

  form.addEventListener("submit", function () {
    submitted = true;
  });
})();
