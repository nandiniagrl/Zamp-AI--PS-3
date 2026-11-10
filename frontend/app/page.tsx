import type { Metadata } from "next";
import { NewProspectForm } from "@/components/workspace/NewProspectForm";

export const metadata: Metadata = { title: "New prospect" };

export default function NewProspectPage() {
  return <NewProspectForm />;
}
