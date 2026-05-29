export function EmptyState({
  icon,
  title,
  description,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12">
      {icon && (
        <div className="h-12 w-12 rounded-full bg-muted text-muted-foreground flex items-center justify-center mb-3">
          {icon}
        </div>
      )}
      <div className="text-sm font-medium">{title}</div>
      {description && (
        <div className="text-xs text-muted-foreground mt-1 max-w-xs">{description}</div>
      )}
    </div>
  );
}
