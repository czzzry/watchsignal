import type { SVGProps } from "react";

export type WatchSignalIconName =
  | "arrow-left"
  | "bookmark"
  | "check"
  | "chevron-down"
  | "chevron-right"
  | "close"
  | "eye"
  | "eye-off"
  | "film"
  | "heart"
  | "history"
  | "info"
  | "lock"
  | "message"
  | "play"
  | "plus"
  | "refresh"
  | "search"
  | "sparkles"
  | "thumbs-down"
  | "thumbs-up"
  | "user"
  | "users";

export type WatchSignalIconProps = Omit<SVGProps<SVGSVGElement>, "children"> & {
  name: WatchSignalIconName;
  title?: string;
};

export function WatchSignalIcon({ name, title, ...props }: WatchSignalIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      {...props}
    >
      {title ? <title>{title}</title> : null}
      <IconGlyph name={name} />
    </svg>
  );
}

function IconGlyph({ name }: { name: WatchSignalIconName }) {
  switch (name) {
    case "arrow-left":
      return <><path d="m15 18-6-6 6-6" /><path d="M9 12h10" /></>;
    case "bookmark":
      return <path d="M6.5 4.75A1.75 1.75 0 0 1 8.25 3h7.5a1.75 1.75 0 0 1 1.75 1.75V21L12 17.6 6.5 21Z" />;
    case "check":
      return <path d="m5 12.5 4.25 4.25L19 7" />;
    case "chevron-down":
      return <path d="m6 9 6 6 6-6" />;
    case "chevron-right":
      return <path d="m9 6 6 6-6 6" />;
    case "close":
      return <><path d="m7 7 10 10" /><path d="M17 7 7 17" /></>;
    case "eye":
      return <><path d="M2.5 12s3.5-5.5 9.5-5.5 9.5 5.5 9.5 5.5-3.5 5.5-9.5 5.5S2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="2.25" /></>;
    case "eye-off":
      return <><path d="m3 3 18 18" /><path d="M10.6 6.6q.7-.1 1.4-.1c6 0 9.5 5.5 9.5 5.5a17 17 0 0 1-2.1 2.6M6.2 6.2C3.8 7.7 2.5 12 2.5 12s3.5 5.5 9.5 5.5q1.7 0 3.1-.5" /></>;
    case "film":
      return <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M7 5v14M17 5v14M3 9h4M17 9h4M3 15h4M17 15h4" /></>;
    case "heart":
      return <path d="M20.8 5.8a5.2 5.2 0 0 0-7.4 0L12 7.2l-1.4-1.4a5.2 5.2 0 0 0-7.4 7.4L12 22l8.8-8.8a5.2 5.2 0 0 0 0-7.4Z" />;
    case "history":
      return <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>;
    case "info":
      return <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>;
    case "lock":
      return <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>;
    case "message":
      return <path d="M20 15a3 3 0 0 1-3 3H9l-5 3v-6a3 3 0 0 1-1-2.2V7a3 3 0 0 1 3-3h11a3 3 0 0 1 3 3Z" />;
    case "play":
      return <path d="m9 7 8 5-8 5Z" fill="currentColor" stroke="none" />;
    case "plus":
      return <><path d="M12 5v14" /><path d="M5 12h14" /></>;
    case "refresh":
      return <><path d="M20 7v5h-5" /><path d="M19 12a7 7 0 1 1-2-5" /></>;
    case "search":
      return <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>;
    case "sparkles":
      return <><path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2Z" /><path d="m18 14 .7 2.3L21 17l-2.3.7L18 20l-.7-2.3L15 17l2.3-.7ZM5 13l.7 2.3L8 16l-2.3.7L5 19l-.7-2.3L2 16l2.3-.7Z" /></>;
    case "thumbs-down":
      return <><path d="M7 4v11H4.5A1.5 1.5 0 0 1 3 13.5v-8A1.5 1.5 0 0 1 4.5 4Z" /><path d="M7 14h5l-1 4.2a2.2 2.2 0 0 0 4.2 1.3L20 9.5A4 4 0 0 0 16.4 4H7" /></>;
    case "thumbs-up":
      return <><path d="M7 20V9H4.5A1.5 1.5 0 0 0 3 10.5v8A1.5 1.5 0 0 0 4.5 20Z" /><path d="M7 10h5l-1-4.2a2.2 2.2 0 0 1 4.2-1.3L20 14.5a4 4 0 0 1-3.6 5.5H7" /></>;
    case "user":
      return <><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></>;
    case "users":
      return <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 5a3.5 3.5 0 0 1 0 6.8M16.5 14.2a6 6 0 0 1 5 5.8" /></>;
  }
}
