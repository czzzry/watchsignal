"use client";

export function SessionRecoveryStep({
  title,
  detail,
  actionLabel,
  onAction,
}: {
  title: string;
  detail: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <section className="wizardPanel sessionPanel" aria-labelledby="recovery-heading">
      <div className="sectionHeading">
        <p className="eyebrow">Session check</p>
        <h2 id="recovery-heading">{title}</h2>
        <p>{detail}</p>
      </div>
      <button type="button" className="primaryAction" onClick={onAction}>
        {actionLabel}
      </button>
    </section>
  );
}
