import { ButtonHTMLAttributes, forwardRef } from "react";
import clsx from "clsx";

export type ButtonVariant = "primary" | "default" | "danger" | "invisible";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "default", size = "md", className, children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
    
    const variantStyles = {
      primary: "bg-gh-success-emphasis text-white hover:bg-gh-success-fg focus:ring-gh-success-emphasis border border-[rgba(31,35,40,0.15)]",
      default: "bg-gh-canvas-subtle text-gh-fg-default hover:bg-gh-neutral-muted border border-gh-border-default focus:ring-gh-accent-emphasis",
      danger: "bg-gh-danger-emphasis text-white hover:bg-gh-danger-fg focus:ring-gh-danger-emphasis border border-[rgba(31,35,40,0.15)]",
      invisible: "text-gh-fg-default hover:bg-gh-neutral-muted focus:ring-gh-accent-emphasis",
    };
    
    const sizeStyles = {
      sm: "px-2 py-1 text-xs",
      md: "px-3 py-1.5 text-sm",
      lg: "px-4 py-2 text-base",
    };
    
    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export { Button };
