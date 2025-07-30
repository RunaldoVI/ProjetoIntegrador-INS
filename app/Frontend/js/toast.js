function showToast(message, type = "error") {
  const toast = document.createElement("div");
  toast.className = "px-4 py-3 rounded shadow-md w-72 text-sm flex items-center gap-3 animate-fade-in-up";
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");

  toast.classList.add(type === "success" ? "bg-green-500" : "bg-red-500", "text-white");
  toast.innerHTML = `<i class="fas ${type === "success" ? "fa-check-circle" : "fa-exclamation-triangle"}"></i><span>${message}</span>`;

  const container = document.getElementById("toastContainer");
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
