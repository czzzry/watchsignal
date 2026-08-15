import { notFound } from "next/navigation";
import { InteractionRemixPrototype } from "./prototype";

export default function InteractionRemixPrototypePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <InteractionRemixPrototype />;
}
