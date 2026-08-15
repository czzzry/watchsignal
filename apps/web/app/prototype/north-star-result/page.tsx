import { notFound } from "next/navigation";
import { NorthStarResultPrototype } from "./prototype";

export default function NorthStarResultPrototypePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <NorthStarResultPrototype />;
}
