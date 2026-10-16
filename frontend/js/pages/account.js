import { api } from "../api.js";
import { logout, requireAuth } from "../auth.js";
import { mountShell } from "../components/shell.js";
import { confirmDialog } from "../components/dialog.js";
import { applyApiErrors, clearAll, setBusy, showFormError } from "../components/forms.js";
import { initial } from "../components/format.js";
import { fillDistricts, getLanguage, mountLanguage, setLanguage } from "../components/lang.js";
import { toast } from "../components/toast.js";
import { getMe, updateMe } from "../session.js";
import { currentLang, hasChosenLang, setLang } from "../i18n.js";

if (requireAuth()) init();

async function init() {
  mountShell("account");
  const $ = (id) => document.getElementById(id);
  const form = $("account-form");
  const seg = $("lang-seg");
  mountLanguage(seg, "rw", "preferred_language");
  fillDistricts($("districts"));

  try {
    const me = await getMe({ fresh: true });
    $("acc-username").textContent = me.username;
    $("acc-avatar").textContent = initial(me.username);
    form.email.value = me.email || "";
    form.phone.value = me.phone || "";
    form.district.value = me.district || "";
    setLanguage(seg, hasChosenLang() ? currentLang() : me.preferred_language || "rw");
  } catch (err) {
    showFormError(form, err.message);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAll(form);
    $("saved-note").textContent = "";
    const button = $("save-btn");
    setBusy(button, true);
    try {
      await updateMe({
        email: form.email.value.trim(),
        phone: form.phone.value.trim(),
        district: form.district.value.trim(),
        preferred_language: getLanguage(seg),
      });
      const chosen = getLanguage(seg);
      if (chosen !== currentLang()) { setLang(chosen); window.location.reload(); return; } // rebuild the page in the new language
      toast("Your changes are saved.");
      $("saved-note").textContent = "Saved";
    } catch (err) {
      if (!applyApiErrors(form, err)) showFormError(form, err.message);
    } finally {
      setBusy(button, false);
    }
  });

  $("logout-btn").addEventListener("click", async () => {
    if (await confirmDialog({ title: "Sign out?", message: "You will need to sign in again to see your checks.", confirmLabel: "Sign out" })) logout();
  });
}
