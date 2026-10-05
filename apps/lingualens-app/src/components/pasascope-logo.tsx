import Image from "next/image";
import Link from "next/link";
import React from "react";

interface PasaScopeLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  showWordmark?: boolean;
  showSubtitle?: boolean;
  subtitle?: string;
  href?: string;
  priority?: boolean;
}

export function PasaScopeLogoMark({
  size = "md",
  className = "",
  priority = false,
}: {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
  priority?: boolean;
}) {
  const dimensions = {
    xs: { w: 37, h: 24 },
    sm: { w: 50, h: 32 },
    md: { w: 65, h: 42 },
    lg: { w: 87, h: 56 },
    xl: { w: 112, h: 72 },
  }[size];

  return (
    <span
      className={`inline-flex items-center justify-center shrink-0 select-none ${className}`}
      style={{ width: dimensions.w, height: dimensions.h }}
      role="img"
      aria-label="PasaScope Logomark"
    >
      <Image
        src="/pasascope-mark-transparent.png"
        alt="PasaScope Logomark"
        width={dimensions.w * 2}
        height={dimensions.h * 2}
        priority={priority}
        className="h-full w-full object-contain"
      />
    </span>
  );
}

export function PasaScopeLogo({
  className = "",
  size = "md",
  showWordmark = true,
  showSubtitle = true,
  subtitle = "ภาษา-สโคป",
  href,
  priority = false,
}: PasaScopeLogoProps) {
  const sizeConfig = {
    sm: {
      markSize: "sm" as const,
      titleClass: "text-base tracking-tight font-bold",
      subClass: "text-[11px] leading-tight font-medium",
      gapClass: "gap-2.5",
    },
    md: {
      markSize: "md" as const,
      titleClass: "text-xl tracking-tight font-bold",
      subClass: "text-xs leading-tight font-medium",
      gapClass: "gap-3",
    },
    lg: {
      markSize: "lg" as const,
      titleClass: "text-2xl tracking-tight font-bold",
      subClass: "text-sm leading-tight font-medium",
      gapClass: "gap-3.5",
    },
    xl: {
      markSize: "xl" as const,
      titleClass: "text-4xl tracking-tight font-extrabold sm:text-5xl",
      subClass: "text-base leading-relaxed font-medium sm:text-lg",
      gapClass: "gap-4 sm:gap-5",
    },
  }[size];

  const content = (
    <div className={`inline-flex items-center ${sizeConfig.gapClass} ${className} select-none`}>
      <PasaScopeLogoMark size={sizeConfig.markSize} priority={priority} />

      {showWordmark && (
        <div className="flex flex-col min-w-0">
          <div className={`flex items-baseline font-sans ${sizeConfig.titleClass}`}>
            <span className="text-[#265347] font-bold">Pasa</span>
            <span className="text-[#F45B69] font-bold">Scope</span>
          </div>
          {showSubtitle && subtitle && (
            <span className={`text-[color:var(--color-text-muted)] ${sizeConfig.subClass}`}>
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="inline-flex transition opacity-95 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded-lg">
        {content}
      </Link>
    );
  }

  return content;
}
