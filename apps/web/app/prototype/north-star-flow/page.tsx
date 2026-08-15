import { notFound } from "next/navigation";
import { NorthStarFlowPrototype } from "./prototype";

export default function NorthStarFlowPrototypePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <NorthStarFlowPrototype />;
}
