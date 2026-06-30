"use client";

import { useMemo, useState } from "react";
import type { SetupLoadResult, SetupProfile } from "./setup-api";

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

export function SetupWizard({ apiHealth, setupLoad }: SetupWizardProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [profiles, setProfiles] = useState(setupLoad.setup.profiles);
  const [savedSnapshot, setSavedSnapshot] = useState(profiles);

  const hasLocalChanges = useMemo(
    () =>
      profiles.some((profile) => {
        const savedProfile = savedSnapshot.find((item) => item.id === profile.id);
        return savedProfile?.label !== profile.label;
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

  function saveLocalReview() {
    setSavedSnapshot(profiles);
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
          <p className="eyebrow">Movie Night Mediator</p>
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
          <button type="button" onClick={saveLocalReview}>
            {setupLoad.canPersist ? "Save setup" : "Keep local review"}
          </button>
        )}
      </footer>
    </main>
  );
}

function ProfilesStep({
  profiles,
  onProfileLabelChange,
}: {
  profiles: SetupProfile[];
  onProfileLabelChange: (profileId: string, label: string) => void;
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
            <label key={profile.id} className="profileField">
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
}: {
  profiles: SetupProfile[];
  canPersist: boolean;
  hasLocalChanges: boolean;
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
            <div key={profile.id}>
              <span>{profile.order}</span>
              <p>{profile.label}</p>
            </div>
          ))}
      </div>
      <p className="readyNote">
        {canPersist
          ? "Backend setup persistence is available for this review."
          : "Backend setup persistence is still blocked by Slice 2. Edits stay on this screen."}
      </p>
      <p className={hasLocalChanges ? "changeNote changeNoteActive" : "changeNote"}>
        {hasLocalChanges ? "Unsaved local label changes" : "Labels match the current review"}
      </p>
    </section>
  );
}

function DefaultItem({ label, value }: { label: string; value: string }) {
  return (
    <article className="defaultItem">
      <span>{label}</span>
      <p>{value}</p>
    </article>
  );
}
