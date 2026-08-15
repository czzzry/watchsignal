import { notFound } from "next/navigation";
import { RedesignGauntletBoard } from "./redesign-gauntlet-board";

export default function RedesignGauntletPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <RedesignGauntletBoard />;
}
