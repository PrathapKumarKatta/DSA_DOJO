import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  ArrowRight,
  Check,
  ChevronsRight,
  LoaderCircle,
  X,
} from "lucide-react";
import { errorMessage } from "./api";

export const ToastContext = createContext<
  (message: string, error?: boolean) => void
>(() => {});
export function useToast() {
  return useContext(ToastContext);
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo">
      <span className="logo-mark">
        <ChevronsRight size={24} strokeWidth={2.6} />
      </span>
      {!compact && (
        <span>
          Task<span className="logo-light">flow</span>
          <span className="logo-period">.</span>
        </span>
      )}
    </div>
  );
}
export function Spinner() {
  return <LoaderCircle className="spin" size={18} aria-label="Loading" />;
}
export function Avatar({
  name,
  small = false,
}: {
  name: string;
  small?: boolean;
}) {
  const initials = name.includes("-")
    ? name.slice(0, 2)
    : name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("");
  return (
    <span className={`avatar ${small ? "small" : ""}`} title={name}>
      {initials.toUpperCase()}
    </span>
  );
}
export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <ChevronsRight size={28} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry: () => void;
}) {
  return (
    <div className="error-state" role="alert">
      <p>{errorMessage(error)}</p>
      <button className="button secondary" onClick={retry}>
        Try again <ArrowRight size={15} />
      </button>
    </div>
  );
}
export function Modal({
  title,
  subtitle,
  children,
  close,
  wide = false,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  close: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const headingId = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    dialog.querySelector<HTMLInputElement>("input:not([readonly])")?.focus();
    return () => {
      dialog.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={headingId}
      className={`modal ${wide ? "wide" : ""}`}
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="modal-head">
        <div>
          <h2 id={headingId}>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <button
          className="icon-button"
          onClick={close}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function useAction() {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try {
      await action();
    } catch (error) {
      toast(errorMessage(error), true);
    } finally {
      setBusy(false);
    }
  }
  return { busy, run };
}
export function SaveButton({
  busy,
  disabled = false,
  children = "Save changes",
}: {
  busy: boolean;
  disabled?: boolean;
  children?: ReactNode;
}) {
  return (
    <button
      type="submit"
      className="button primary"
      disabled={busy || disabled}
    >
      {busy ? <Spinner /> : <Check size={16} />}
      {children}
    </button>
  );
}
export function formatDate(date: string | null) {
  return date
    ? new Date(date).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      })
    : "No due date";
}
export function formatTime(date: string) {
  return new Date(date).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
