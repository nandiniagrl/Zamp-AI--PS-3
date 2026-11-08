import type { Metadata } from "next";
import { NewProspectFormB } from "@/components/b/NewProspectForm";

export const metadata: Metadata = { title: "New prospect" };

export default function NewProspectB() {
  return <NewProspectFormB />;
}
