import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import styles from "./primitives.module.css";

type BrandProps = HTMLAttributes<HTMLDivElement> & {
  compact?: boolean;
};

export function WatchSignalBrand({ compact = false, className, ...props }: BrandProps) {
  return (
    <div className={[styles.brand, className].filter(Boolean).join(" ")} {...props}>
      <span className={styles.mark} aria-hidden="true">W</span>
      {compact ? null : <strong className={styles.brandName}>WatchSignal</strong>}
    </div>
  );
}

export function WatchSignalHeader({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLElement> & { children?: ReactNode }) {
  return (
    <header className={[styles.header, className].filter(Boolean).join(" ")} {...props}>
      <WatchSignalBrand />
      {children ? <div className={styles.headerEnd}>{children}</div> : null}
    </header>
  );
}

export type WatchSignalButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type WatchSignalButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: WatchSignalButtonVariant;
};

export function WatchSignalButton({
  className,
  type = "button",
  variant = "primary",
  ...props
}: WatchSignalButtonProps) {
  return (
    <button
      className={[
        styles.button,
        styles[variant],
        className,
      ].filter(Boolean).join(" ")}
      type={type}
      {...props}
    />
  );
}

type WatchSignalIconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  variant?: WatchSignalButtonVariant;
};

export function WatchSignalIconButton({
  children,
  className,
  label,
  type = "button",
  variant = "secondary",
  ...props
}: WatchSignalIconButtonProps) {
  return (
    <button
      className={[
        styles.iconButton,
        variant === "primary" ? null : styles[variant],
        className,
      ].filter(Boolean).join(" ")}
      type={type}
      aria-label={label}
      {...props}
    >
      {children}
    </button>
  );
}
