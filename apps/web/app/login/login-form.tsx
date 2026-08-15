"use client";

import { FormEvent, useRef, useState } from "react";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import { WatchSignalBrand, WatchSignalButton } from "../ui/primitives";
import styles from "./login.module.css";

type LoginPhase = "idle" | "submitting" | "error" | "success";

export function LoginForm() {
  const [message, setMessage] = useState("");
  const [phase, setPhase] = useState<LoginPhase>("idle");
  const [showPassword, setShowPassword] = useState(false);
  const passwordInput = useRef<HTMLInputElement>(null);
  const busy = phase === "submitting" || phase === "success";

  function recoverAtPassphrase() {
    window.requestAnimationFrame(() => passwordInput.current?.select());
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }

    const form = new FormData(event.currentTarget);
    const password = form.get("password");
    if (typeof password !== "string" || !password) {
      setMessage("Enter your household passphrase.");
      setPhase("error");
      recoverAtPassphrase();
      return;
    }

    setMessage("Checking your passphrase…");
    setPhase("submitting");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    }).catch(() => null);

    if (!response?.ok) {
      setMessage(
        response?.status === 401
          ? "That passphrase isn’t right. Try again."
          : response
            ? "WatchSignal isn’t available right now. Try again."
            : "Can’t reach WatchSignal. Check your connection and try again.",
      );
      setPhase("error");
      recoverAtPassphrase();
      return;
    }

    setMessage("Signed in. Opening WatchSignal…");
    setPhase("success");
    window.location.assign("/");
  }

  return (
    <section className={styles.loginSurface} aria-labelledby="login-title">
      <header className={styles.loginHeader}>
        <WatchSignalBrand />
      </header>

      <form className={styles.loginForm} onSubmit={submit} noValidate>
        <div className={styles.loginIntro}>
          <span className={styles.householdGlyph} aria-hidden="true">
            <WatchSignalIcon name="users" />
          </span>
          <h1 id="login-title">Welcome back.</h1>
          <p>Continue to your household.</p>
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="household-password">Household passphrase</label>
          <div className={styles.passwordField} data-invalid={phase === "error" || undefined}>
            <WatchSignalIcon className={styles.fieldIcon} name="lock" />
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
              aria-invalid={phase === "error"}
              aria-describedby="login-feedback login-session-note"
              autoFocus
              disabled={busy}
              onChange={() => {
                if (phase === "error") {
                  setMessage("");
                  setPhase("idle");
                }
              }}
            />
            <button
              className={styles.passwordToggle}
              type="button"
              aria-label={showPassword ? "Hide passphrase" : "Show passphrase"}
              aria-pressed={showPassword}
              disabled={busy}
              onClick={() => setShowPassword((visible) => !visible)}
            >
              <WatchSignalIcon name={showPassword ? "eye-off" : "eye"} />
            </button>
          </div>
          <p
            className={styles.feedback}
            data-state={phase}
            id="login-feedback"
            role={phase === "error" ? "alert" : "status"}
            aria-live="polite"
          >
            {message}
          </p>
        </div>

        <WatchSignalButton className={styles.continueButton} type="submit" disabled={busy}>
          {phase === "success" ? (
            <><WatchSignalIcon name="check" />Opening…</>
          ) : phase === "submitting" ? (
            "Checking…"
          ) : (
            "Continue"
          )}
        </WatchSignalButton>

        <p className={styles.sessionNote} id="login-session-note">
          <WatchSignalIcon name="lock" />
          This phone stays signed in for 90 days.
        </p>
      </form>
    </section>
  );
}
