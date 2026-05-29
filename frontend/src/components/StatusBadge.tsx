type Tone = "default" | "success" | "warning" | "info" | "destructive" | "muted";

const tones: Record<Tone, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-success/15 text-success",
  warning: "bg-warning/20 text-warning-foreground",
  info: "bg-info/15 text-info",
  destructive: "bg-destructive/15 text-destructive",
  muted: "bg-muted text-muted-foreground",
};

export function StatusBadge({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): Tone {
  switch (status) {
    case "Active":
    case "Completed":
    case "Engaged":
      return "success";
    case "Paused":
    case "Queued":
    case "In Review":
      return "info";
    case "Error":
    case "Failed":
      return "destructive";
    case "Running":
    case "Piloting":
      return "default";
    case "New":
      return "info";
    default:
      return "muted";
  }
}

export function priorityTone(p: string): Tone {
  switch (p) {
    case "Critical":
      return "destructive";
    case "High":
      return "warning";
    case "Medium":
      return "info";
    case "Low":
      return "muted";
    default:
      return "default";
  }
}
