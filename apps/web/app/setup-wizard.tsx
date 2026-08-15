"use client";

import { useEffect, useMemo, useState, type MouseEvent } from "react";
import {
  saveSetupState,
  type SetupLoadResult,
  type SetupProfile,
  type SetupState,
} from "./setup-api";
import {
  clearSetupFromPhone,
  keepSetupOnPhone,
  loadStoredSetupFromPhone,
  normalizeSetup,
  setupStatesMatch,
  updateSetupProfile,
} from "./setup-local-state";
import { WatchSignalIcon } from "./ui/watchsignal-icons";
import { WatchSignalBrand } from "./ui/primitives";
import styles from "./setup-wizard.module.css";

type SetupSaveStatus =
  | "clean"
  | "unsaved"
  | "saving"
  | "saved"
  | "failed"
  | "local-only";

type SetupWizardProps = {
  setupLoad: SetupLoadResult;
};

const avatarOptions = [
  { key: "spark", label: "Spark", symbol: "S" },
  { key: "moon", label: "Moon", symbol: "M" },
  { key: "comet", label: "Comet", symbol: "C" },
  { key: "ticket", label: "Ticket", symbol: "T" },
];
const colorOptions = [
  { key: "cyan", label: "Cyan" },
  { key: "rose", label: "Rose" },
  { key: "amber", label: "Amber" },
  { key: "violet", label: "Violet" },
];

export function SetupWizard({ setupLoad }: SetupWizardProps) {
  const [setup, setSetup] = useState(setupLoad.setup);
  const [savedSnapshot, setSavedSnapshot] = useState(setupLoad.setup);
  const [saveStatus, setSaveStatus] = useState<SetupSaveStatus>(
    setupLoad.canPersist ? "clean" : "local-only",
  );
  const [saveMessage, setSaveMessage] = useState(
    setupLoad.canPersist
      ? "Everything is up to date."
      : "You’re offline. Changes can stay on this phone.",
  );
  const [localSnapshotKept, setLocalSnapshotKept] = useState(false);

  const hasUnsavedChanges = useMemo(
    () => !setupStatesMatch(setup, savedSnapshot),
    [setup, savedSnapshot],
  );
  const sortedProfiles = useMemo(
    () => [...setup.profiles].sort((first, second) => first.order - second.order),
    [setup.profiles],
  );

  useEffect(() => {
    const stored = loadStoredSetupFromPhone(window.localStorage);
    if (!stored) return;
    setSetup(stored.setup);
    setSavedSnapshot(stored.setup);
    setLocalSnapshotKept(true);
    setSaveStatus("local-only");
    setSaveMessage(
      setupLoad.canPersist
        ? "Kept on this phone. Save to share these changes."
        : "Kept on this phone.",
    );
  }, [setupLoad.canPersist]);

  useEffect(() => {
    function warnBeforeUnload(event: BeforeUnloadEvent) {
      if (!hasUnsavedChanges) return;
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [hasUnsavedChanges]);

  function updateProfile(profileId: string, change: Partial<SetupProfile>) {
    setSetup((current) => updateSetupProfile(current, profileId, change));
    setSaveStatus("unsaved");
    setSaveMessage("Changes not saved yet.");
  }

  function normalizedSetup(): SetupState {
    return normalizeSetup(setup);
  }

  async function saveSetup(): Promise<void> {
    if (!setupLoad.canPersist) {
      keepOnPhone();
      return;
    }

    const nextSetup = normalizedSetup();
    setSetup(nextSetup);
    setSaveStatus("saving");
    setSaveMessage("Saving…");
    const result = await saveSetupState(nextSetup);
    if (!result.canPersist) {
      setSaveStatus("failed");
      setSaveMessage("Couldn’t save. Your changes are still here.");
      return;
    }

    setSetup(result.setup);
    setSavedSnapshot(result.setup);
    clearSetupFromPhone(window.localStorage);
    setLocalSnapshotKept(false);
    setSaveStatus("saved");
    setSaveMessage("Saved for your household.");
  }

  function keepOnPhone(): void {
    const nextSetup = normalizedSetup();
    setSetup(nextSetup);
    try {
      const keptSetup = keepSetupOnPhone(window.localStorage, nextSetup);
      setSetup(keptSetup);
      setSavedSnapshot(keptSetup);
      setLocalSnapshotKept(true);
      setSaveStatus("local-only");
      setSaveMessage("Kept on this phone.");
    } catch {
      setSaveStatus("failed");
      setSaveMessage("Couldn’t keep this on your phone. Your changes are still here.");
    }
  }

  function leaveSetup(event: MouseEvent<HTMLAnchorElement>): void {
    if (!hasUnsavedChanges) return;
    if (!window.confirm("Leave without saving these changes?")) event.preventDefault();
  }

  const actionDisabled =
    saveStatus === "saving" ||
    (setupLoad.canPersist && !hasUnsavedChanges && !localSnapshotKept && saveStatus !== "failed") ||
    (!setupLoad.canPersist && localSnapshotKept && !hasUnsavedChanges);

  return (
    <main className={styles.shell} data-save-state={saveStatus}>
      <header className={styles.header}>
        <a href="/" aria-label="Back to WatchSignal" onClick={leaveSetup}>
          <WatchSignalBrand />
        </a>
        <span>Setup</span>
      </header>

      <section className={styles.intro} aria-labelledby="setup-title">
        <span>Household</span>
        <h1 id="setup-title">Make it yours</h1>
        <p>Names and tonight’s usual starting point.</p>
      </section>

      <section className={styles.section} aria-labelledby="profiles-title">
        <div className={styles.sectionHeading}>
          <h2 id="profiles-title">Who’s watching?</h2>
          <span>{sortedProfiles.length} profiles</span>
        </div>
        <div className={styles.profileList}>
          {sortedProfiles.map((profile) => (
            <article className={styles.profile} key={profile.id}>
              <span
                className={`${styles.avatar} ${styles[`avatar${profile.colorKey}`] ?? ""}`}
                aria-hidden="true"
              >
                {avatarSymbol(profile.avatarKey)}
              </span>
              <label className={styles.nameField}>
                <span>Profile {profile.order}</span>
                <input
                  value={profile.label}
                  onChange={(event) => updateProfile(profile.id, { label: event.target.value })}
                  autoComplete="off"
                  maxLength={28}
                />
              </label>
              <div className={styles.identityChoices}>
                <label>
                  <span>Icon</span>
                  <select
                    aria-label={`Icon for ${profile.label}`}
                    value={profile.avatarKey}
                    onChange={(event) => updateProfile(profile.id, { avatarKey: event.target.value })}
                  >
                    {avatarOptions.map((option) => (
                      <option key={option.key} value={option.key}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Color</span>
                  <select
                    aria-label={`Color for ${profile.label}`}
                    value={profile.colorKey}
                    onChange={(event) => updateProfile(profile.id, { colorKey: event.target.value })}
                  >
                    {colorOptions.map((option) => (
                      <option key={option.key} value={option.key}>{option.label}</option>
                    ))}
                  </select>
                </label>
              </div>
            </article>
          ))}
        </div>
      </section>

      <DefaultsReview setup={setup} />

      <section className={styles.actionArea} aria-label="Save setup">
        <p
          className={saveStatus === "failed" ? styles.error : undefined}
          role={saveStatus === "failed" ? "alert" : "status"}
          aria-live="polite"
        >
          {saveMessage}
        </p>
        {saveStatus === "failed" && setupLoad.canPersist ? (
          <div className={styles.recoveryActions}>
            <button type="button" className={styles.secondary} onClick={keepOnPhone}>
              Keep on this phone
            </button>
            <button type="button" className={styles.primary} onClick={() => void saveSetup()}>
              Try again
            </button>
          </div>
        ) : (
          <button
            type="button"
            className={styles.primary}
            onClick={() => void saveSetup()}
            disabled={actionDisabled}
          >
            {saveStatus === "saving"
              ? "Saving…"
              : setupLoad.canPersist
                ? actionDisabled && !localSnapshotKept
                  ? "Saved"
                  : "Save setup"
                : localSnapshotKept && !hasUnsavedChanges
                  ? "Kept on this phone"
                  : "Keep on this phone"}
            {saveStatus !== "saving" && !actionDisabled ? <WatchSignalIcon name="chevron-right" /> : null}
          </button>
        )}
        <a className={styles.back} href="/" onClick={leaveSetup}>
          <WatchSignalIcon name="arrow-left" />
          Back to WatchSignal
        </a>
      </section>
    </main>
  );
}

function DefaultsReview({ setup }: { setup: SetupState }) {
  const activeLabel = profileLabel(setup.activeProfileId, setup.profiles);
  const partnerLabel = profileLabel(setup.partnerProfileId, setup.profiles);
  const defaults = setup.defaults;
  const rows = [
    ["Watching", `${activeLabel} + ${partnerLabel}`],
    ["Language", defaults.languageAccess],
    ["Available on", defaults.availabilityRegion],
    ["How it works", `${defaults.sessionType} · ${defaults.inputMode}`],
    [
      "Shortlist",
      `${defaults.shortlistSize} movies · Watched titles ${defaults.avoidAlreadyWatched ? "hidden" : "included"}`,
    ],
  ];

  return (
    <section className={styles.section} aria-labelledby="defaults-title">
      <div className={styles.sectionHeading}>
        <h2 id="defaults-title">Tonight starts here</h2>
        <span>Review</span>
      </div>
      <dl className={styles.defaults}>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function profileLabel(profileId: string, profiles: SetupProfile[]): string {
  return profiles.find((profile) => profile.id === profileId)?.label || "Profile";
}

function avatarSymbol(avatarKey: string): string {
  return avatarOptions.find((option) => option.key === avatarKey)?.symbol ?? "P";
}
