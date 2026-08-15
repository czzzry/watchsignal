import { notFound } from "next/navigation";
import { LlmJourneyPrototype } from "./prototype";

export default function LlmJourneyPrototypePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <LlmJourneyPrototype />;
}
