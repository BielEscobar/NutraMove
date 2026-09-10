import { VersionEditor } from "@/components/diets/version-editor";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <VersionEditor id={id} />;
}
