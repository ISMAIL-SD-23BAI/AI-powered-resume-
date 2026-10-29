const API = "http://127.0.0.1:8000";

// Already logged in → skip straight to dashboard
if (localStorage.getItem("token")) window.location.href = "dashboard.html";

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorMsg = document.getElementById("error-msg");
  const btn = document.getElementById("submit-btn");
  errorMsg.textContent = "";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  btn.disabled = true;
  btn.textContent = "Logging in…";

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Login failed");

    localStorage.setItem("token", data.access_token);
    window.location.href = "dashboard.html";
  } catch (err) {
    errorMsg.textContent = err.message;
    btn.disabled = false;
    btn.textContent = "Log In";
  }
});
