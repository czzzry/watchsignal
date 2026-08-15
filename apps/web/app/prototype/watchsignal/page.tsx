import { notFound } from "next/navigation";
import { PrototypeStudio } from "./prototype-studio";

export default function WatchSignalPrototypePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <PrototypeStudio />;
}
