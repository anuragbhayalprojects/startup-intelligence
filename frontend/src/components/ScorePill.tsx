import { cn } from "@/lib/utils";

interface ScorePillProps {
  value: number;
  className?: string;
}

export function ScorePill({ value, className }: ScorePillProps) {
  const tone =
    value >= 75
      ? "bg-success/10 text-success border-success/20"
      : value >= 50
        ? "bg-warning/10 text-warning border-warning/20"
        : "bg-muted text-muted-foreground border-border";
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center min-w-10 px-2 py-0.5 rounded-md border text-xs font-semibold tabular-nums",
        tone,
        className,
      )}
    >
      {value}
    </span>
  );
}
