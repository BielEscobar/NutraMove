import { VersionDetail } from "@/components/diets/version-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <VersionDetail area="master" id={id} />;
}
