(() => {
 const form = document.getElementById("contactForm");
 if (!form) return;
 const status = document.getElementById("contactStatus");
 const token = document.getElementById("contactSubmissionId");
 const submit = form.querySelector('[type="submit"]');
 let busy = false;
 form.addEventListener("submit", async event => {
  event.preventDefault();
  if (busy || !form.reportValidity()) return;
  if (!token.value) token.value = crypto.randomUUID();
  busy = true;
  submit.disabled = true;
  status.textContent = "Отправляем заявку…";
  try {
   const response = await fetch(form.action, {
    method: "POST", body: new FormData(form), credentials: "same-origin"
   });
   const data = await response.json();
   if (!response.ok) {
    status.textContent = data.errors
     ? Object.values(data.errors).flat().map(error => error.message).join(" ")
     : "Не удалось отправить заявку. Попробуйте ещё раз.";
    return;
   }
   form.reset();
   token.value = "";
   status.textContent = data.message;
  } catch {
   status.textContent = "Нет связи с сервером. Проверьте подключение и повторите отправку.";
  } finally {
   busy = false;
   submit.disabled = false;
  }
 });
})();
