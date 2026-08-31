/**
 * School Planner Generator — Client-side logic.
 *
 * Non-blocking async form submission. No frameworks, no dependencies.
 * Sends the ICS URL to the API, receives a PDF blob, triggers download.
 */

(function () {
  "use strict";

  // Injected at deploy time by CI/CD (see .github/workflows/deploy.yml)
  const API_URL = "__API_URL__";

  const form = document.getElementById("planner-form");
  const submitBtn = document.getElementById("submit-btn");
  const btnText = submitBtn.querySelector(".btn-text");
  const btnSpinner = submitBtn.querySelector(".btn-spinner");
  const statusEl = document.getElementById("status");
  const icsInput = document.getElementById("ics-url");
  const rememberCheckbox = document.getElementById("remember");
  const savedStatus = document.getElementById("saved-status");
  const savedStatusText = document.getElementById("saved-status-text");
  const clearSavedBtn = document.getElementById("clear-saved");

  // ---------------------------------------------------------------------------
  // Browser-only persistence (localStorage)
  //
  // Everything here stays on the user's own device. The saved data is only ever
  // read back into the form on this same machine and is never transmitted to us
  // beyond the API call the user already makes by clicking Generate.
  //
  // Note on encryption: we intentionally store the URL in plaintext. Encrypting
  // it client-side would be security theater — with no server, the key would
  // have to live in the same localStorage. Honest plaintext + explicit user
  // control + a shared-computer warning is the trustworthy choice.
  // ---------------------------------------------------------------------------
  const STORAGE_KEY = "school-planner:saved";
  const STORAGE_VERSION = 1;
  const EXPIRY_DAYS = 90;
  const EXPIRY_MS = EXPIRY_DAYS * 24 * 60 * 60 * 1000;

  function safeGetItem() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch {
      return null; // private mode / storage disabled
    }
  }

  function safeSetItem(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // Storage unavailable (private mode, quota). Persistence is best-effort;
      // never let it break the generate flow.
    }
  }

  function safeRemoveItem() {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // no-op
    }
  }

  function loadSaved() {
    const raw = safeGetItem();
    if (!raw) return null;
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      safeRemoveItem(); // corrupt — discard
      return null;
    }
    // Discard unknown schema versions and expired data.
    if (!parsed || parsed.version !== STORAGE_VERSION) {
      safeRemoveItem();
      return null;
    }
    if (!parsed.lastUsed || Date.now() - parsed.lastUsed > EXPIRY_MS) {
      safeRemoveItem();
      return null;
    }
    return parsed;
  }

  function saveForm(fields) {
    safeSetItem(
      JSON.stringify({
        version: STORAGE_VERSION,
        lastUsed: Date.now(),
        fields,
      })
    );
  }

  function purgeSaved() {
    safeRemoveItem();
    updateSavedStatus(null);
  }

  function daysUntilExpiry(lastUsed) {
    const remaining = EXPIRY_MS - (Date.now() - lastUsed);
    return Math.max(0, Math.ceil(remaining / (24 * 60 * 60 * 1000)));
  }

  function updateSavedStatus(saved) {
    if (!saved) {
      savedStatus.hidden = true;
      savedStatusText.textContent = "";
      return;
    }
    const days = daysUntilExpiry(saved.lastUsed);
    savedStatusText.textContent = `Restored from this browser · expires in ${days} day${
      days === 1 ? "" : "s"
    } if unused`;
    savedStatus.hidden = false;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearStatus();
    clearError();

    const icsUrl = icsInput.value.trim();
    const studentName = document.getElementById("student-name").value.trim();
    const grade = document.getElementById("grade").value;
    const theme = document.getElementById("theme").value;
    const combineBlocks = document.getElementById("combine-blocks").checked;

    // Client-side validation
    if (!icsUrl) {
      showError("Please paste your ICS calendar feed URL.");
      icsInput.classList.add("error");
      icsInput.focus();
      return;
    }

    if (!icsUrl.startsWith("https://")) {
      showError("The URL must start with https://");
      icsInput.classList.add("error");
      icsInput.focus();
      return;
    }

    // Start loading state
    setLoading(true);
    showStatus("Fetching your schedule and generating the planner...", "loading");

    try {
      const payload = { ics_url: icsUrl };
      if (studentName) payload.student_name = studentName;
      if (grade) payload.grade = parseInt(grade, 10);
      if (theme) payload.theme = theme;
      if (combineBlocks) payload.combine_blocks = true;

      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let message = "Something went wrong. Please try again.";
        try {
          const err = await response.json();
          if (err.error) message = err.error;
        } catch {
          // Response wasn't JSON, use default message
        }
        showError(message);
        return;
      }

      // Success — download the PDF
      const blob = await response.blob();
      const filename = studentName ? `${studentName}_planner.pdf` : "planner.pdf";
      downloadBlob(blob, filename);
      showStatus("Your planner is ready! Check your downloads.", "success");

      // Persist the form if the user opted in (refreshes the 90-day timer).
      if (rememberCheckbox.checked) {
        saveForm({
          ics_url: icsUrl,
          student_name: studentName,
          grade,
          theme,
          combine_blocks: combineBlocks,
        });
        updateSavedStatus(loadSaved());
      }
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        showError("Could not connect to the server. Please check your internet connection.");
      } else {
        showError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  });

  // Clear error styling when user starts typing
  icsInput.addEventListener("input", () => {
    icsInput.classList.remove("error");
  });

  // Update the theme description line when the selection changes
  const themeSelect = document.getElementById("theme");
  const themeDescription = document.getElementById("theme-description");
  themeSelect.addEventListener("change", () => {
    const selected = themeSelect.options[themeSelect.selectedIndex];
    const description = selected.getAttribute("data-description");
    if (description) {
      themeDescription.textContent = description;
    }
  });

  // Unchecking "remember" purges saved data immediately (full control).
  rememberCheckbox.addEventListener("change", () => {
    if (!rememberCheckbox.checked) {
      purgeSaved();
    }
  });

  // Explicit "Clear saved data" button: wipe storage and reset the opt-in.
  clearSavedBtn.addEventListener("click", () => {
    purgeSaved();
    rememberCheckbox.checked = false;
  });

  // On load: restore saved form data if present and not expired.
  function restoreSavedForm() {
    const saved = loadSaved();
    if (!saved || !saved.fields) return;
    const f = saved.fields;
    if (f.ics_url) icsInput.value = f.ics_url;
    if (f.student_name) document.getElementById("student-name").value = f.student_name;
    if (f.grade) document.getElementById("grade").value = f.grade;
    if (f.theme) {
      themeSelect.value = f.theme;
      themeSelect.dispatchEvent(new Event("change")); // sync description line
    }
    document.getElementById("combine-blocks").checked = Boolean(f.combine_blocks);
    rememberCheckbox.checked = true;
    updateSavedStatus(saved);
  }

  restoreSavedForm();

  function setLoading(loading) {
    submitBtn.disabled = loading;
    btnText.textContent = loading ? "Generating..." : "Generate Planner";
    btnSpinner.hidden = !loading;
  }

  function showStatus(message, type) {
    statusEl.textContent = message;
    statusEl.className = `status status--${type}`;
    statusEl.hidden = false;
  }

  function showError(message) {
    showStatus(message, "error");
  }

  function clearStatus() {
    statusEl.hidden = true;
    statusEl.className = "status";
    statusEl.textContent = "";
  }

  function clearError() {
    icsInput.classList.remove("error");
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    // Cleanup
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  }
})();
