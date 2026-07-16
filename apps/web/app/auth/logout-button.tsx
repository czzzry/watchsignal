"use client";

import { useEffect, useState } from "react";

export function LogoutButton() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    void fetch("/api/auth/status")
      .then((response) => response.json())
      .then((payload: unknown) => {
        setEnabled(
          typeof payload === "object" &&
            payload !== null &&
            "enabled" in payload &&
            payload.enabled === true,
        );
      })
      .catch(() => setEnabled(false));
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.assign("/login");
  }

  if (!enabled) {
    return null;
  }

  return (
    <button className="footerAction" type="button" onClick={logout}>
      Sign out
    </button>
  );
}
