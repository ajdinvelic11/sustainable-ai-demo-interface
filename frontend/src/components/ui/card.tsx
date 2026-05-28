import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

function Card({ children, className, ...props }: CardProps) {
  return (
    <div className={clsx("glass-panel rounded-xl p-5", className)} {...props}>
      {children}
    </div>
  );
}

export { Card };
export default Card;
