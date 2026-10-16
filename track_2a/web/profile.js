"use strict";
(() => {
  const header = document.querySelector(".workspace-topbar");
  if (!header) return;
  const profile = document.createElement("div");
  profile.className = "profile";
  profile.innerHTML = `<button class="profile-toggle" type="button" aria-label="Open profile" aria-expanded="false" aria-controls="profile-panel"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></svg></button>
    <div id="profile-panel" class="profile-panel" role="dialog" aria-labelledby="profile-title" hidden>
      <div class="profile-heading"><h2 id="profile-title">Your profile</h2><button type="button" class="profile-close" aria-label="Close profile">×</button></div>
      <p>Your name is used for review decisions.</p>
      <form class="profile-form"><label for="profile-name">Name</label><input id="profile-name" name="name" autocomplete="name" maxlength="80" required placeholder="Your name">
      <label for="profile-email">Email</label><input id="profile-email" name="email" type="email" autocomplete="email" maxlength="254" placeholder="you@example.com">
      <p class="profile-note">Saved in this browser.</p><button class="profile-save" type="submit">Save profile</button><p class="profile-feedback" role="status" aria-live="polite"></p></form>
    </div>`;
  header.append(profile);
  const toggle = profile.querySelector(".profile-toggle"), panel = profile.querySelector(".profile-panel");
  const name = profile.querySelector("#profile-name"), email = profile.querySelector("#profile-email");
  const feedback = profile.querySelector(".profile-feedback"), reviewer = document.getElementById("reviewer");
  function read(key) { try { return localStorage.getItem(key) || ""; } catch { return ""; } }
  function load() { name.value = read("skony.reviewer") || reviewer?.value || ""; email.value = read("skony.profile.email"); }
  function avatar() {
    const saved = read("skony.reviewer");
    if (saved && saved !== "Local reviewer") toggle.textContent = saved.trim().split(/\s+/).slice(0, 2).map(part => Array.from(part)[0]).join("").toUpperCase();
  }
  function close(restoreFocus = true) { panel.hidden = true; toggle.setAttribute("aria-expanded", "false"); if (restoreFocus) toggle.focus(); }
  toggle.addEventListener("click", () => {
    if (!panel.hidden) return close();
    load(); feedback.textContent = ""; panel.hidden = false; toggle.setAttribute("aria-expanded", "true"); name.focus();
  });
  profile.querySelector(".profile-close").addEventListener("click", () => close());
  document.addEventListener("click", event => { if (!panel.hidden && !profile.contains(event.target)) close(false); });
  profile.addEventListener("keydown", event => { if (event.key === "Escape") { event.preventDefault(); close(); } });
  profile.querySelector("form").addEventListener("submit", event => {
    event.preventDefault();
    name.value = name.value.trim(); email.value = email.value.trim();
    if (!name.value) { name.focus(); name.reportValidity(); return; }
    try {
      localStorage.setItem("skony.reviewer", name.value); localStorage.setItem("skony.profile.email", email.value);
      if (reviewer) { reviewer.value = name.value; reviewer.dispatchEvent(new Event("change", {bubbles:true})); }
      avatar(); feedback.textContent = "Profile saved.";
    } catch { feedback.textContent = "Browser storage is unavailable. Your profile could not be saved."; }
  });
  load(); avatar();
})();
