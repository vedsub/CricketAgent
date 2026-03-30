const form = document.getElementById("analysis-form");
const statusNode = document.getElementById("status");
const resultNode = document.getElementById("result");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const apiBase = document.getElementById("api-base").value.replace(/\/$/, "");
  const payload = {
    own_team: document.getElementById("own-team").value.trim(),
    opponent: document.getElementById("opponent").value.trim(),
    venue: document.getElementById("venue").value.trim(),
    format: document.getElementById("format").value,
    squad: document
      .getElementById("squad")
      .value.split("\n")
      .map((name) => name.trim())
      .filter(Boolean),
  };

  statusNode.textContent = "Running analysis...";
  resultNode.textContent = JSON.stringify(payload, null, 2);

  try {
    const response = await fetch(`${apiBase}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    statusNode.textContent = "Analysis complete.";
    resultNode.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    statusNode.textContent = "Request failed.";
    resultNode.textContent = JSON.stringify(
      {
        error: error.message,
      },
      null,
      2
    );
  }
});
