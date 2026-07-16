import { cva, type VariantProps } from "class-variance-authority";
import type {
  InputHTMLAttributes,
  LabelHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

/**
 * Form-field primitives. Hand-rolled on the locked tokens (the codebase is
 * bespoke CVA; native `<input>/<textarea>/<input type=checkbox>` are fully
 * accessible). Styling is token-only: `border-hairline-strong` input border, the
 * GLOBAL accent-deep `:focus-visible` ring from globals.css (these add
 * `focus-visible:outline-none` only to suppress the browser default, never to
 * hide focus), and the `destructive` token for the error state (driven off
 * `aria-invalid` so the caller flips one attribute). Inputs are ~44px (touch).
 *
 * A11y wiring is the caller's job: pair `<Label htmlFor>` with the control `id`,
 * point `aria-describedby` at the `<FieldError id>`, and set `aria-invalid` on
 * error. `<FieldError>` is `aria-live` so validation messages are announced.
 */

export const labelVariants = cva(
  "block text-body-sm font-medium text-charcoal",
);

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, ...props }: LabelProps) {
  return <label className={cn(labelVariants(), className)} {...props} />;
}

const controlBase =
  "w-full rounded-md border border-hairline-strong bg-surface px-3.5 text-body-md text-ink placeholder:text-steel transition-colors focus-visible:outline-none hover:border-steel disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-destructive";

export const inputVariants = cva(cn(controlBase, "min-h-[46px] py-2.5"));
export const textareaVariants = cva(cn(controlBase, "min-h-28 py-2.5"));

export interface InputProps
  extends
    InputHTMLAttributes<HTMLInputElement>,
    VariantProps<typeof inputVariants> {}

export function Input({ className, type = "text", ...props }: InputProps) {
  return (
    <input type={type} className={cn(inputVariants(), className)} {...props} />
  );
}

export interface TextareaProps
  extends
    TextareaHTMLAttributes<HTMLTextAreaElement>,
    VariantProps<typeof textareaVariants> {}

export function Textarea({ className, ...props }: TextareaProps) {
  return <textarea className={cn(textareaVariants(), className)} {...props} />;
}

export interface CheckboxProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  "type"
> {}

/**
 * Native checkbox sized for touch (`size-5`), tinted to the accent via
 * `accent-green`. The label/consent copy is rendered by the caller alongside it.
 */
export function Checkbox({ className, ...props }: CheckboxProps) {
  return (
    <input
      type="checkbox"
      className={cn(
        "mt-0.5 size-5 shrink-0 rounded-sm border border-hairline-strong accent-green focus-visible:outline-none aria-[invalid=true]:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

export interface FieldErrorProps {
  id: string;
  children?: string;
  className?: string;
}

/**
 * Inline validation message. Renders nothing (but stays in the tree as an
 * `aria-live` region) until `children` is set, so newly-shown errors are
 * announced. Pair its `id` with the control's `aria-describedby`.
 */
export function FieldError({ id, children, className }: FieldErrorProps) {
  return (
    <p
      id={id}
      role="alert"
      aria-live="polite"
      className={cn("min-h-[1.25rem] text-body-sm text-destructive", className)}
    >
      {children}
    </p>
  );
}
