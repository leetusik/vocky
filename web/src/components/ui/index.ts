// Barrel for the token-driven UI primitives. Pages import components + their CVA
// fns from "@/components/ui". These now carry the vocky design system (round 01):
// deep-emerald tokens, compact density, split Badge, and the new Select / Chip.
export { Button, buttonVariants } from "./button";
export type { ButtonProps } from "./button";

export { Card, cardVariants } from "./card";
export type { CardProps } from "./card";

export { Badge, badgeVariants } from "./badge";
export type { BadgeProps } from "./badge";

export { Section, sectionVariants } from "./section";
export type { SectionProps } from "./section";

export { Grid } from "./grid";
export type { GridProps } from "./grid";

export { EndpointCard } from "./endpoint-card";
export type { EndpointCardProps } from "./endpoint-card";

// New primitive (P4.S1) — headless, token-styled table for the S3/S4/S5 lists.
export { DataTable } from "./data-table";
export type { DataTableColumn, DataTableProps } from "./data-table";

// Scroll-reveal wrapper — progressive-enhancement, reduced-motion-safe.
export { Reveal } from "./reveal";
export type { RevealProps } from "./reveal";

// Form-field primitives — hand-rolled on the locked tokens.
export {
  Checkbox,
  FieldError,
  Input,
  inputVariants,
  Label,
  labelVariants,
  Textarea,
  textareaVariants,
} from "./field";
export type {
  CheckboxProps,
  FieldErrorProps,
  InputProps,
  LabelProps,
  TextareaProps,
} from "./field";

// Styled native <select> — the a11y-preserving replacement for raw
// `<select className={inputVariants()}>` filter controls.
export { Select, selectVariants } from "./select";
export type { SelectProps } from "./select";

// Small mono tag/pill — feedback tags + removable active-filter pills.
export { Chip, chipVariants } from "./chip";
export type { ChipProps } from "./chip";
