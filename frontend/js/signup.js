const API = "http://127.0.0.1:8000";

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorMsg = document.getElementById("error-msg");
  const btn = document.getElementById("submit-btn");
  errorMsg.textContent = "";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirm = document.getElementById("confirm").value;
  const full_name = document.getElementById("full-name").value.trim() || undefined;

  if (password !== confirm) {
    errorMsg.textContent = "Passwords do not match.";
    return;
  }
  if (password.length < 8) {
    errorMsg.textContent = "Password must be at least 8 characters.";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Creating…";

  try {
    const res = await fetch(`${API}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? "Signup failed");

    // auto-login after successful registration
    const loginRes = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const loginData = await loginRes.json();
    if (!loginRes.ok) throw new Error(loginData.detail ?? "Login failed after signup");

    localStorage.setItem("token", loginData.access_token);
    window.location.href = "dashboard.html";
  } catch (err) {
    errorMsg.textContent = err.message;
    btn.disabled = false;
    btn.textContent = "Create Account";
  }
});
