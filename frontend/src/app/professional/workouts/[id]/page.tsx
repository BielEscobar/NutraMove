import { WorkoutHistory } from "@/components/workouts/workout-history";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <WorkoutHistory area="professional" id={id} />;
}
