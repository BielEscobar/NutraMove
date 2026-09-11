import { WorkoutList } from "@/components/workouts/workout-list";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <WorkoutList area="professional" studentId={id} />;
}
