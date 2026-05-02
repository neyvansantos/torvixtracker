"use client";

// Copyright (c) 2026 Torvix Tracker. Todos os direitos reservados.

import { motion, HTMLMotionProps } from "framer-motion";
import { ReactNode } from "react";

interface RevealSectionProps extends HTMLMotionProps<"section"> {
  children: ReactNode;
  delay?: number;
}

export function RevealSection({
  children,
  delay = 0,
  className,
  ...props
}: RevealSectionProps) {
  return (
    <motion.section
      className={className}
      initial={{ opacity: 0, y: 30 }}
      transition={{
        duration: 0.8,
        delay: delay,
        ease: [0.21, 0.47, 0.32, 0.98],
      }}
      viewport={{ once: true, margin: "-100px" }}
      whileInView={{ opacity: 1, y: 0 }}
      {...props}
    >
      {children}
    </motion.section>
  );
}
