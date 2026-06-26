const steps = [
  "Set up household profiles",
  "Start shared movie night",
  "React to five safe picks",
  "Hand phone over",
  "Review tonight's recommendation",
];

export default function Home() {
  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Local mobile MVP</p>
        <h1>Movie Night Mediator</h1>
        <p className="lede">
          A pass-the-phone recommender for finding something watchable tonight.
        </p>
        <div className="actions">
          <button type="button">Start setup</button>
          <button type="button" className="secondary">
            Open demo session
          </button>
        </div>
      </section>
      <section className="flow" aria-label="MVP flow">
        {steps.map((step, index) => (
          <article key={step} className="flowStep">
            <span>{index + 1}</span>
            <p>{step}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
