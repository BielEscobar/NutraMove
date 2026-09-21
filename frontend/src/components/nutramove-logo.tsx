import Image from "next/image";

export function NutraMoveLogo({
  className = "h-auto w-40",
  priority = false,
}: {
  className?: string;
  priority?: boolean;
}) {
  return (
    <Image
      src="/brand/nutramove-logo.png"
      alt="NutraMove"
      width={1536}
      height={1024}
      className={`object-contain ${className}`}
      priority={priority}
    />
  );
}
