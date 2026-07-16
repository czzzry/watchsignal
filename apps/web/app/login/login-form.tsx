"use client";

import { FormEvent, useRef, useState } from "react";

export function LoginForm() {
  const [message, setMessage] = useState("Enter your household passphrase to continue.");
  const [hasError, setHasError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const passwordInput = useRef<HTMLInputElement>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = form.get("password");
    if (typeof password !== "string" || !password) {
      setMessage("Enter the household passphrase.");
      setHasError(true);
      passwordInput.current?.focus();
      return;
    }

    setBusy(true);
    setHasError(false);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }).catch(() => null);

    if (!response?.ok) {
      const payload = (await response?.json().catch(() => null)) as
        | { detail?: unknown }
        | null;
      setMessage(
        typeof payload?.detail === "string"
          ? payload.detail
          : "WatchSignal could not sign in. Check the connection and try again.",
      );
      setHasError(true);
      setBusy(false);
      passwordInput.current?.select();
      return;
    }

    window.location.assign("/");
  }

  return (
    <form className="loginCard" onSubmit={submit}>
      <div className="loginIdentity">
        <img src="/icons/watchsignal-192.png" alt="" width="88" height="88" />
        <div>
          <p className="eyebrow">Private household</p>
          <h1>Welcome back</h1>
        </div>
      </div>
      <p
        className={hasError ? "loginMessage loginMessageError" : "loginMessage"}
        role={hasError ? "alert" : "status"}
        aria-live="polite"
      >
        {message}
      </p>
      <label className="loginPasswordLabel" htmlFor="household-password">
        Household passphrase
      </label>
      <div className="loginPasswordField">
        <input
          ref={passwordInput}
          id="household-password"
          name="password"
          type={showPassword ? "text" : "password"}
          autoComplete="current-password"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="go"
          aria-invalid={hasError}
          aria-describedby="login-session-note"
          autoFocus
          required
        />
        <button
          className="loginPasswordToggle"
          type="button"
          aria-label={showPassword ? "Hide passphrase" : "Show passphrase"}
          aria-pressed={showPassword}
          onClick={() => setShowPassword((visible) => !visible)}
        >
          {showPassword ? "Hide" : "Show"}
        </button>
      </div>
      <p className="loginSessionNote" id="login-session-note">
        You’ll stay signed in on this phone for 90 days.
      </p>
      <button type="submit" disabled={busy}>
        {busy ? "Opening…" : "Continue"}
      </button>
    </form>
  );
}
