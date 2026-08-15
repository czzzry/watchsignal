import { notFound } from "next/navigation";
import { SystemFoundationHarness } from "./system-foundation-harness";

export default function SystemFoundationPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return <SystemFoundationHarness />;
}
