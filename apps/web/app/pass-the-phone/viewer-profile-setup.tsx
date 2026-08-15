"use client";

import { useEffect, useState, type RefObject } from "react";
import type { PeopleMode } from "../pass-the-phone-model";
import type { SetupProfile } from "../setup-api";
import { AccessibleModal } from "../ui/accessible-modal";
import { WatchSignalIcon } from "../ui/watchsignal-icons";
import {
  hasDistinctViewerProfiles,
  profileNameIssue,
  viewerModeOptions,
  viewerSetupMessage,
} from "./viewer-profile-contract";
import styles from "./viewer-profile-setup.module.css";

export function ViewerProfileSetup({
  backgroundRef,
  opener,
  founderLabel,
  wifeLabel,
  peopleMode,
  profiles,
  activeProfileId,
  partnerProfileId,
  busy,
  message,
  canPersist,
  onPeopleModeChange,
  onActiveProfileChange,
  onPartnerProfileChange,
  onCreateProfile,
  onClose,
}: {
  backgroundRef: RefObject<HTMLElement | null>;
  opener: HTMLElement | null;
  founderLabel: string;
  wifeLabel: string;
  peopleMode: PeopleMode;
  profiles: SetupProfile[];
  activeProfileId: string;
  partnerProfileId: string;
  busy: boolean;
  message: string | null;
  canPersist: boolean;
  onPeopleModeChange: (mode: PeopleMode) => void;
  onActiveProfileChange: (profileId: string) => void | Promise<void>;
  onPartnerProfileChange: (profileId: string) => void | Promise<void>;
  onCreateProfile: (label: string) => void | Promise<void>;
  onClose: () => void;
}) {
  const [newProfileName, setNewProfileName] = useState("");
  const [createPendingName, setCreatePendingName] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<"selection" | "create">("selection");
  const duplicateIssue = newProfileName ? profileNameIssue(newProfileName, profiles) : null;
  const distinct = hasDistinctViewerProfiles(
    peopleMode,
    activeProfileId,
    partnerProfileId,
  );
  const publicMessage = viewerSetupMessage(message, lastAction);

  useEffect(() => {
    if (
      createPendingName &&
      profiles.some(
        (profile) =>
          profile.label.trim().toLocaleLowerCase() ===
          createPendingName.trim().toLocaleLowerCase(),
      )
    ) {
      setNewProfileName("");
      setCreatePendingName(null);
    }
  }, [createPendingName, profiles]);

  async function createProfile(): Promise<void> {
    const issue = profileNameIssue(newProfileName, profiles);
    if (issue) {
      return;
    }
    setLastAction("create");
    setCreatePendingName(newProfileName.trim());
    await onCreateProfile(newProfileName.trim());
  }

  return (
    <AccessibleModal
      backgroundRef={backgroundRef}
      opener={opener}
      onClose={onClose}
      layerClassName={styles.layer}
      backdropClassName={styles.backdrop}
      dialogClassName={styles.dialog}
      labelledBy="viewer-profile-title"
    >
      <header className={styles.header}>
        <div>
          <span>People</span>
          <h2 id="viewer-profile-title">Who’s watching?</h2>
        </div>
        <button type="button" onClick={onClose} aria-label="Close people settings" autoFocus>
          <WatchSignalIcon name="close" />
        </button>
      </header>

      <div className={styles.scroll}>
        <div className={styles.modeList} role="group" aria-label="Viewer mode">
          {viewerModeOptions(founderLabel, wifeLabel).map((option) => (
            <button
              key={option.value}
              type="button"
              data-selected={option.value === peopleMode || undefined}
              aria-pressed={option.value === peopleMode}
              onClick={() => onPeopleModeChange(option.value)}
            >
              <span aria-hidden="true"><i /><i /></span>
              <strong>{option.label}</strong>
              <small>{option.detail}</small>
              <WatchSignalIcon name="check" />
            </button>
          ))}
        </div>

        <section className={styles.identitySection} aria-labelledby="stored-identities-title">
          <div className={styles.sectionHeading}>
            <h3 id="stored-identities-title">Stored identities</h3>
            <span>{canPersist ? "Household profiles" : "Available on this phone"}</span>
          </div>
          <ProfileSelect
            label={peopleMode === "couple" ? "Person one" : "Watching as"}
            value={peopleMode === "wife" ? partnerProfileId : activeProfileId}
            profiles={profiles}
            disabled={busy}
            onChange={peopleMode === "wife" ? onPartnerProfileChange : onActiveProfileChange}
          />
          {peopleMode === "couple" ? (
            <ProfileSelect
              label="Person two"
              value={partnerProfileId}
              profiles={profiles.filter((profile) => profile.id !== activeProfileId)}
              disabled={busy}
              onChange={onPartnerProfileChange}
            />
          ) : null}
        </section>

        <form
          className={styles.createProfile}
          onSubmit={(event) => {
            event.preventDefault();
            void createProfile();
          }}
        >
          <label htmlFor="new-profile-name">Add a profile</label>
          <div>
            <input
              id="new-profile-name"
              value={newProfileName}
              onChange={(event) => setNewProfileName(event.target.value)}
              placeholder="Name"
              maxLength={28}
              disabled={busy}
              aria-invalid={Boolean(duplicateIssue)}
              aria-describedby="profile-create-status"
            />
            <button type="submit" disabled={busy || Boolean(profileNameIssue(newProfileName, profiles))}>
              Add
            </button>
          </div>
          <p id="profile-create-status" data-error={Boolean(duplicateIssue && newProfileName) || undefined} role="status" aria-live="polite">
            {duplicateIssue && newProfileName ? duplicateIssue : publicMessage ?? "Names can be up to 28 characters."}
          </p>
        </form>
      </div>

      <footer className={styles.footer}>
        {!distinct ? <p role="alert">Choose two different profiles.</p> : null}
        <button type="button" onClick={onClose} disabled={busy || !distinct}>
          {busy ? "Saving…" : "Continue"}
        </button>
      </footer>
    </AccessibleModal>
  );
}

function ProfileSelect({
  label,
  value,
  profiles,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  profiles: SetupProfile[];
  disabled: boolean;
  onChange: (profileId: string) => void | Promise<void>;
}) {
  return (
    <label className={styles.profileSelect}>
      <span>{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => void onChange(event.target.value)}
      >
        {profiles.map((profile) => (
          <option key={profile.id} value={profile.id}>{profile.label}</option>
        ))}
      </select>
    </label>
  );
}
