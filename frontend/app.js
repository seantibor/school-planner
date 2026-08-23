/**
 * Pine Crest Planner Generator — Client-side logic.
 *
 * Non-blocking async form submission. No frameworks, no dependencies.
 * Sends the ICS URL to the API, receives a PDF blob, triggers download.
 */

(function () {
  "use strict";

  // TODO: Replace with actual deployed API URL
  const API_URL = "https://YOUR_API_GATEWAY_URL/generate";

  const form = document.getElementById("planner-form");
  const submitBtn = document.getElementById("submit-btn");
  const btnText = submitBtn.querySelector(".btn-text");
  const btnSpinner = submitBtn.querySelector(".btn-spinner");
  const statusEl = document.getElementById("status");
  const icsInput = document.getElementById("ics-url");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearStatus();
    clearError();

    const icsUrl = icsInput.value.trim();
    const studentName = document.getElementById("student-name").value.trim();
    const grade = document.getElementById("grade").value;

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
