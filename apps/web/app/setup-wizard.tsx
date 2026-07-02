"use client";

import { useMemo, useState } from "react";
import {
  saveSetupState,
  type SetupLoadResult,
  type SetupProfile,
} from "./setup-api";

type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

type SetupWizardProps = {
  apiHealth: ApiHealth;
  setupLoad: SetupLoadResult;
};

const profileStepLabels = ["Profiles", "Defaults", "Ready"];
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

export function SetupWizard({ apiHealth, setupLoad }: SetupWizardProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [profiles, setProfiles] = useState(setupLoad.setup.profiles);
  const [savedSnapshot, setSavedSnapshot] = useState(profiles);
  const [saveMessage, setSaveMessage] = useState(setupLoad.detail);
  const [isSaving, setIsSaving] = useState(false);

  const hasLocalChanges = useMemo(
    () =>
      profiles.some((profile) => {
        const savedProfile = savedSnapshot.find((item) => item.id === profile.id);
        return (
          savedProfile?.label !== profile.label ||
          savedProfile?.avatarKey !== profile.avatarKey ||
          savedProfile?.colorKey !== profile.colorKey
        );
      }),
    [profiles, savedSnapshot],
  );

  function updateProfileLabel(profileId: string, label: string) {
    setProfiles((currentProfiles) =>
      currentProfiles.map((profile) =>
        profile.id === profileId ? { ...profile, label } : profile,
      ),
    );
  }

  function updateProfileAvatar(profileId: string, avatarKey: string) {
    setProfiles((currentProfiles) =>
      currentProfiles.map((profile) =>
        profile.id === profileId ? { ...profile, avatarKey } : profile,
      ),
    );
  }

  function updateProfileColor(profileId: string, colorKey: string) {
    setProfiles((currentProfiles) =>
      currentProfiles.map((profile) =>
        profile.id === profileId ? { ...profile, colorKey } : profile,
      ),
    );
  }

  async function saveSetup() {
    const nextProfiles = profiles.map((profile) => ({
      ...profile,
      label: profile.label.trim() || `Profile ${profile.order}`,
    }));
    setProfiles(nextProfiles);
    setIsSaving(true);
    const result = setupLoad.canPersist
      ? await saveSetupState({
          ...setupLoad.setup,
          profiles: nextProfiles,
        })
      : {
          setup: {
            ...setupLoad.setup,
            profiles: nextProfiles,
          },
          detail: "Setup API is unavailable. Edits are kept for this screen.",
        };

    setSavedSnapshot(result.setup.profiles);
    setSaveMessage(result.detail);
    setIsSaving(false);
    setActiveStep(2);
  }

  function resetDefaults() {
    setProfiles(setupLoad.setup.profiles);
    setSavedSnapshot(setupLoad.setup.profiles);
    setActiveStep(0);
  }

  return (
    <main className="appShell">
      <header className="topBar">
        <div>
          <p className="eyebrow">WatchSignal</p>
          <h1>Setup</h1>
        </div>
        <div
          className={
            apiHealth.connected
              ? "connectionPill connectionPillConnected"
              : "connectionPill connectionPillDisconnected"
          }
          role="status"
          aria-label={`FastAPI health ${apiHealth.label}`}
          title={apiHealth.detail}
        >
          <span aria-hidden="true" />
          <strong>{apiHealth.label}</strong>
        </div>
      </header>

      <section className="setupStatus" aria-label="Setup API status">
        <div>
          <p>{setupLoad.source === "backend" ? "Backend setup" : "Local defaults"}</p>
          <small>{setupLoad.detail}</small>
        </div>
      </section>

      <nav className="stepTabs" aria-label="Setup steps">
        {profileStepLabels.map((label, index) => (
          <button
            key={label}
            type="button"
            className={activeStep === index ? "stepTab stepTabActive" : "stepTab"}
            onClick={() => setActiveStep(index)}
          >
            <span>{index + 1}</span>
            {label}
          </button>
        ))}
      </nav>

      {activeStep === 0 ? (
        <ProfilesStep
          profiles={profiles}
          onProfileLabelChange={updateProfileLabel}
          onProfileAvatarChange={updateProfileAvatar}
          onProfileColorChange={updateProfileColor}
        />
      ) : null}

      {activeStep === 1 ? (
        <DefaultsStep setupLoad={setupLoad} profiles={profiles} />
      ) : null}

      {activeStep === 2 ? (
        <ReadyStep
          profiles={profiles}
          canPersist={setupLoad.canPersist}
          hasLocalChanges={hasLocalChanges}
          saveMessage={saveMessage}
        />
      ) : null}

      <footer className="bottomActions">
        <button
          type="button"
          className="secondaryButton"
          onClick={activeStep === 0 ? resetDefaults : () => setActiveStep(activeStep - 1)}
        >
          {activeStep === 0 ? "Reset" : "Back"}
        </button>
        {activeStep < 2 ? (
          <button type="button" onClick={() => setActiveStep(activeStep + 1)}>
            Continue
          </button>
        ) : (
          <button type="button" onClick={saveSetup} disabled={isSaving}>
            {isSaving
              ? "Saving..."
              : setupLoad.canPersist
                ? "Save setup"
                : "Keep local review"}
          </button>
        )}
      </footer>
    </main>
  );
}

function ProfilesStep({
  profiles,
  onProfileLabelChange,
  onProfileAvatarChange,
  onProfileColorChange,
}: {
  profiles: SetupProfile[];
  onProfileLabelChange: (profileId: string, label: string) => void;
  onProfileAvatarChange: (profileId: string, avatarKey: string) => void;
  onProfileColorChange: (profileId: string, colorKey: string) => void;
}) {
  return (
    <section className="wizardPanel" aria-labelledby="profiles-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Household profiles</p>
        <h2 id="profiles-heading">Who is taking turns?</h2>
      </div>
      <div className="profileList">
        {profiles
          .slice()
          .sort((first, second) => first.order - second.order)
          .map((profile) => (
            <article key={profile.id} className="profileIdentityCard">
              <label className="profileField">
                <span>Profile {profile.order}</span>
                <input
                  value={profile.label}
                  onChange={(event) =>
                    onProfileLabelChange(profile.id, event.target.value)
                  }
                  autoComplete="off"
                  maxLength={28}
                />
              </label>
              <div className="profileIdentityControls">
                <div className="profileChoiceGroup">
                  <span>Avatar</span>
                  <div className="profileAvatarChoices" role="group" aria-label={`Avatar for ${profile.label}`}>
                    {avatarOptions.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        className={
                          profile.avatarKey === option.key
                            ? "profileAvatarChoice profileAvatarChoiceActive"
                            : "profileAvatarChoice"
                        }
                        onClick={() => onProfileAvatarChange(profile.id, option.key)}
                        title={option.label}
                      >
                        {option.symbol}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="profileChoiceGroup">
                  <span>Color</span>
                  <div className="profileColorChoices" role="group" aria-label={`Color for ${profile.label}`}>
                    {colorOptions.map((option) => (
                      <button
                        key={option.key}
                        type="button"
                        className={
                          profile.colorKey === option.key
                            ? `profileColorChoice profileColorChoiceActive profileColorChoice${option.key}`
                            : `profileColorChoice profileColorChoice${option.key}`
                        }
                        onClick={() => onProfileColorChange(profile.id, option.key)}
                        title={option.label}
                      >
                        <span />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </article>
          ))}
      </div>
    </section>
  );
}

function DefaultsStep({
  setupLoad,
  profiles,
}: {
  setupLoad: SetupLoadResult;
  profiles: SetupProfile[];
}) {
  const defaults = setupLoad.setup.defaults;
  const firstProfile = profiles[0]?.label || "Profile 1";
  const secondProfile = profiles[1]?.label || "Profile 2";

  return (
    <section className="wizardPanel" aria-labelledby="defaults-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Household defaults</p>
        <h2 id="defaults-heading">Tonight starts from here</h2>
      </div>
      <div className="defaultGrid">
        <DefaultItem label="Session" value={defaults.sessionType} />
        <DefaultItem label="Input" value={defaults.inputMode} />
        <DefaultItem label="Profiles" value={`${firstProfile} then ${secondProfile}`} />
        <DefaultItem label="Availability" value={defaults.availabilityRegion} />
        <DefaultItem label="Language" value={defaults.languageAccess} />
        <DefaultItem
          label="Shortlist"
          value={`${defaults.shortlistSize} titles, already watched hidden`}
        />
      </div>
    </section>
  );
}

function ReadyStep({
  profiles,
  canPersist,
  hasLocalChanges,
  saveMessage,
}: {
  profiles: SetupProfile[];
  canPersist: boolean;
  hasLocalChanges: boolean;
  saveMessage: string;
}) {
  return (
    <section className="wizardPanel" aria-labelledby="ready-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Ready check</p>
        <h2 id="ready-heading">Setup is reviewable</h2>
      </div>
      <div className="handoffPreview">
        {profiles
          .slice()
          .sort((first, second) => first.order - second.order)
          .map((profile) => (
            <div key={profile.id} className={`identityPreview identityPreview${profile.colorKey}`}>
              <span>{avatarSymbol(profile.avatarKey)}</span>
              <p>{profile.label}</p>
            </div>
          ))}
      </div>
      <p className="readyNote">
        {saveMessage ||
          (canPersist
            ? "Backend setup persistence is available for this review."
            : "Backend setup persistence is unavailable. Edits stay on this screen.")}
      </p>
      <p className={hasLocalChanges ? "changeNote changeNoteActive" : "changeNote"}>
        {hasLocalChanges ? "Unsaved local label changes" : "Labels match the current review"}
      </p>
    </section>
  );
}

function avatarSymbol(avatarKey: string): string {
  return avatarOptions.find((option) => option.key === avatarKey)?.symbol ?? "P";
}

function DefaultItem({ label, value }: { label: string; value: string }) {
  return (
    <article className="defaultItem">
      <span>{label}</span>
      <p>{value}</p>
    </article>
  );
}
