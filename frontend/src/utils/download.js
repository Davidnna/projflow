export function triggerDownload(url, filename) {
    if (!url) {
        throw new Error("The document download link is unavailable.");
    }

    const link = document.createElement("a");
    link.href = url;
    link.download = filename || "project-report";
    link.rel = "noopener";
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
}