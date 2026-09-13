import type { User } from "./api";
export type Notification = {
  id: string;
  type: string;
  title: string;
  message: string;
  resource_type: string;
  resource_id: string;
  read_at: string | null;
  created_at: string;
};
export type NotificationList = {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
};
export function notificationLink(
  item: Notification,
  role: User["role"],
): string | null {
  const id = encodeURIComponent(item.resource_id);
  if (role === "STUDENT") {
    if (item.type === "DIET_UPDATED") return "/student/diet";
    if (item.type === "WORKOUT_UPDATED") return "/student/workout";
    if (item.type === "INFORMATION_PUBLISHED")
      return `/student/informations/${id}`;
    if (
      [
        "REEVALUATION_IN_REVIEW",
        "REEVALUATION_COMPLETED",
        "REEVALUATION_CANCELLED",
      ].includes(item.type)
    )
      return `/student/reevaluation-requests/${id}`;
  }
  if (role === "PROFESSIONAL") {
    if (item.type === "REEVALUATION_CREATED")
      return `/professional/reevaluation-requests/${id}`;
    if (item.type === "STUDENT_PENDING_APPROVAL")
      return `/professional/students/${id}`;
  }
  return null;
}
export function refreshNotificationCount() {
  window.dispatchEvent(new Event("notifications-read"));
}
