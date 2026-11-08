import type { Metadata } from "next";
import { NewProspectFormA } from "@/components/a/NewProspectForm";

export const metadata: Metadata = { title: "New prospect" };

export default function NewProspectA() {
  return <NewProspectFormA />;
}
