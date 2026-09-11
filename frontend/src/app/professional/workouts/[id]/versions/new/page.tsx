import { WorkoutEditor } from "@/components/workouts/workout-editor";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <WorkoutEditor
      path={`/professional/workouts/${id}/versions`}
      backHref={`/professional/workouts/${id}`}
    />
  );
}
