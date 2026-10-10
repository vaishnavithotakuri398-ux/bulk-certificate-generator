
const form = document.getElementById("upload-form");
const fileInput = document.getElementById("recipient-file");
const dropZone = document.getElementById("drop-zone");
const fileTitle = document.getElementById("file-title");
const fileDescription = document.getElementById("file-description");
const generateButton = document.getElementById("generate-button");
const buttonText = document.getElementById("button-text");

const resultsPanel = document.getElementById("results-panel");
const resultTitle = document.getElementById("result-title");
const resultMessage = document.getElementById("result-message");
const resultStatus = document.getElementById("result-status");
const totalCount = document.getElementById("total-count");
const successCount = document.getElementById("success-count");
const failureCount = document.getElementById("failure-count");
const recipientResults = document.getElementById("recipient-results");
const rawResponse = document.getElementById("raw-response");

let selectedFile = null;

fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files[0] || null;
  showSelectedFile();
});

function showSelectedFile() {
  if (!selectedFile) {
    fileTitle.textContent = "Choose an Excel or CSV file";
    fileDescription.textContent = "Click here to browse your computer";
    return;
  }

  fileTitle.textContent = selectedFile.name;
  fileDescription.textContent =
    `${(selectedFile.size / 1024).toFixed(1)} KB · Ready to upload`;
}

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-over");
  });
});

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;

  const extension = file.name.split(".").pop().toLowerCase();

  if (!["xlsx", "csv"].includes(extension)) {
    alert("Please select an .xlsx or .csv file.");
    return;
  }

  try {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    selectedFile = file;
    showSelectedFile();
  } catch {
    alert("Please use Choose File to select your spreadsheet.");
  }
});

function findNestedValue(object, keys) {
  if (!object || typeof object !== "object") return undefined;

  for (const key of keys) {
    if (object[key] !== undefined && object[key] !== null) {
      return object[key];
    }
  }

  for (const value of Object.values(object)) {
    if (value && typeof value === "object") {
      const found = findNestedValue(value, keys);
      if (found !== undefined) return found;
    }
  }

  return undefined;
}

function findRecipientList(object) {
  if (!object || typeof object !== "object") return [];

  if (Array.isArray(object)) {
    if (
      object.length &&
      object.some(item =>
        item &&
        typeof item === "object" &&
        ("recipient_id" in item || "recipientId" in item)
      )
    ) {
      return object;
    }

    for (const item of object) {
      const found = findRecipientList(item);
      if (found.length) return found;
    }

    return [];
  }

  for (const [key, value] of Object.entries(object)) {
    if (
      ["results", "recipients", "certificates"].includes(key) &&
      Array.isArray(value)
    ) {
      return value;
    }
  }

  for (const value of Object.values(object)) {
    const found = findRecipientList(value);
    if (found.length) return found;
  }

  return [];
}

function addCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value ?? "—";
  row.appendChild(cell);
  return cell;
}

function renderResults(data) {
  resultsPanel.hidden = false;
  rawResponse.textContent = JSON.stringify(data, null, 2);

  const jobId = findNestedValue(data, ["job_id", "jobId"]);
  const recipients = findRecipientList(data);

  const total = Number(
    findNestedValue(data, ["total_count", "totalCount"]) ??
    recipients.length ??
    0
  );

  const success = Number(
    findNestedValue(data, ["success_count", "successCount"]) ??
    recipients.filter(item =>
      ["SUCCESS", "COMPLETED", "GENERATED"].includes(
        String(item.status || "").toUpperCase()
      )
    ).length
  );

  const failure = Number(
    findNestedValue(data, ["failure_count", "failureCount"]) ??
    recipients.filter(item =>
      ["FAILED", "ERROR"].includes(String(item.status || "").toUpperCase())
    ).length
  );

  resultTitle.textContent = jobId !== undefined
    ? `Job #${jobId} results`
    : "Generation results";

  resultMessage.textContent =
    data.message || "The server has returned a response.";

  totalCount.textContent = total;
  successCount.textContent = success;
  failureCount.textContent = failure;

  const status = String(
    findNestedValue(data, ["status"]) || "Response received"
  ).toUpperCase();

  resultStatus.textContent = status.replaceAll("_", " ");

  recipientResults.replaceChildren();

  if (!recipients.length) {
    const row = document.createElement("tr");
    const cell = addCell(
      row,
      "No individual recipient results were returned by the API."
    );
    cell.colSpan = 3;
    recipientResults.appendChild(row);
  } else {
    recipients.forEach((recipient) => {
      const row = document.createElement("tr");

      addCell(row, recipient.name || recipient.email || "Recipient");

      const statusCell = addCell(
        row,
        recipient.status || "Processed"
      );
      statusCell.className = "row-status";

      const normalizedStatus = String(
        recipient.status || ""
      ).toUpperCase();

      statusCell.classList.add(
        ["SUCCESS", "COMPLETED", "GENERATED"].includes(normalizedStatus)
          ? "success"
          : ["FAILED", "ERROR"].includes(normalizedStatus)
            ? "failed"
            : ""
      );

      const downloadCell = document.createElement("td");
      const recipientId = recipient.recipient_id ?? recipient.recipientId;

      if (recipientId !== undefined && recipientId !== null) {
        const link = document.createElement("a");
        link.className = "download-link";
        link.href =
          `/api/recipients/${encodeURIComponent(recipientId)}/download`;
        link.textContent = "Download PDF ↗";
        link.setAttribute("download", "");
        downloadCell.appendChild(link);
      } else {
        downloadCell.textContent = "Not available";
      }

      row.appendChild(downloadCell);
      recipientResults.appendChild(row);
    });
  }

  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const eventName = document.getElementById("event-name").value.trim();
  const file = selectedFile || fileInput.files[0];

  if (!eventName) {
    alert("Please enter the event name.");
    return;
  }

  if (!file) {
    alert("Please select an Excel or CSV file.");
    return;
  }

  const extension = file.name.split(".").pop().toLowerCase();

  if (!["xlsx", "csv"].includes(extension)) {
    alert("Only .xlsx and .csv files are supported.");
    return;
  }

  const formData = new FormData();
  formData.append("event_name", eventName);
  formData.append("file", file);

  generateButton.disabled = true;
  buttonText.textContent = "Generating certificates…";
  resultsPanel.hidden = true;

  try {
    const response = await fetch("/api/jobs/upload-and-generate", {
      method: "POST",
      body: formData
    });

    const responseText = await response.text();
    let data;

    try {
      data = JSON.parse(responseText);
    } catch {
      data = { detail: responseText || "The server returned an empty response." };
    }

    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail || data)
      );
    }

    renderResults(data);
  } catch (error) {
    resultsPanel.hidden = false;
    resultTitle.textContent = "Generation unsuccessful";
    resultMessage.textContent =
      error.message || "Could not connect to the server.";
    resultStatus.textContent = "Error";
    totalCount.textContent = "—";
    successCount.textContent = "—";
    failureCount.textContent = "—";
    recipientResults.replaceChildren();
    rawResponse.textContent = error.stack || error.message;
  } finally {
    generateButton.disabled = false;
    buttonText.textContent = "Upload & generate certificates";
  }
});



const downloadAllBtn = document.getElementById("downloadAllBtn");

if (downloadAllBtn) {
    downloadAllBtn.addEventListener("click", async () => {
        downloadAllBtn.disabled = true;
        downloadAllBtn.textContent = "Preparing ZIP...";

        try {
            const response = await fetch(
                "/api/certificates/download-all"
            );

            if (!response.ok) {
                let message = "Could not download certificates.";

                try {
                    const data = await response.json();
                    message = data.detail || message;
                } catch (_) {}

                throw new Error(message);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = "all_certificates.zip";
            document.body.appendChild(link);
            link.click();
            link.remove();

            URL.revokeObjectURL(url);
        } catch (error) {
            alert(error.message);
        } finally {
            downloadAllBtn.disabled = false;
            downloadAllBtn.textContent =
                "Download All Certificates (ZIP)";
        }
    });
}

