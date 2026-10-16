/* Inline validation helpers. A field looks like:
   <div class="field"><label for="x">…</label><input id="x" class="input" aria-describedby="x-error">
   <p class="field-error" id="x-error"><span></span></p></div> */
const fieldOf = (input) => input.closest(".field");

export function setError(input, message) {
  const field = fieldOf(input);
  if (!field) return;
  field.classList.add("has-error");
  input.setAttribute("aria-invalid", "true");
  const err = field.querySelector(".field-error span");
  if (err) err.textContent = message;
}

export function clearError(input) {
  const field = fieldOf(input);
  if (!field) return;
  field.classList.remove("has-error");
  input.removeAttribute("aria-invalid");
}

export function clearAll(form) {
  form.querySelectorAll(".input, .select").forEach(clearError);
  const banner = form.querySelector("[data-form-error]");
  if (banner) banner.hidden = true;
}

export function showFormError(form, message) {
  const banner = form.querySelector("[data-form-error]");
  if (!banner) return;
  banner.querySelector("[data-form-error-text]").textContent = message;
  banner.hidden = false;
  banner.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

/** Map DRF field errors ({username:["…"]}) onto inputs. Returns true if anything was mapped. */
export function applyApiErrors(form, err) {
  const body = err?.details;
  let mapped = false;
  let first = null;
  if (body && typeof body === "object") {
    for (const [name, msgs] of Object.entries(body)) {
      const input = form.elements[name];
      const isField = input && (input.classList?.contains("input") || input.classList?.contains("select"));
      if (isField) {
        setError(input, [].concat(msgs).join(" "));
        first ??= input;
        mapped = true;
      }
    }
  }
  first?.focus();
  return mapped;
}

export function setBusy(button, busy) {
  button.classList.toggle("is-loading", busy);
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

/** Validate on blur, re-validate while typing once a field has been flagged. */
export function bindValidation(form, rules) {
  const run = (input) => {
    const message = rules[input.name]?.(input.value.trim(), input);
    message ? setError(input, message) : clearError(input);
    return !message;
  };
  for (const name of Object.keys(rules)) {
    const input = form.elements[name];
    input.addEventListener("blur", () => run(input));
    input.addEventListener("input", () => { if (fieldOf(input).classList.contains("has-error")) run(input); });
  }
  return () => {
    let ok = true, first = null;
    for (const name of Object.keys(rules)) {
      const input = form.elements[name];
      if (!run(input)) { ok = false; first ??= input; }
    }
    first?.focus();
    return ok;
  };
}

export function bindPasswordToggle(button, input) {
  button.addEventListener("click", () => {
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    button.setAttribute("aria-pressed", String(show));
    button.querySelector("use").setAttribute("href", show ? "#i-eye-off" : "#i-eye");
  });
}
