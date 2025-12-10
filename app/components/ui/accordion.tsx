import * as React from "react"

import { cn } from "@/lib/utils"

const Accordion = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="accordion"
      className={cn("divide-y rounded-xl border", className)}
      {...props}
    />
  )
)
Accordion.displayName = "Accordion"

const AccordionItem = ({ className, ...props }: React.ComponentProps<"div">) => (
  <div data-slot="accordion-item" className={cn("border-none", className)} {...props} />
)

const AccordionTrigger = ({ className, children }: React.ComponentProps<"button">) => (
  <button
    data-slot="accordion-trigger"
    className={cn(
      "flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-medium",
      className
    )}
  >
    {children}
  </button>
)

const AccordionContent = ({ className, ...props }: React.ComponentProps<"div">) => (
  <div data-slot="accordion-content" className={cn("px-4 pb-4 text-sm", className)} {...props} />
)

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
