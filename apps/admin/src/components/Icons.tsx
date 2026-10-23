import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export function OverviewIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="2" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="2" />
    </Icon>
  );
}

export function UsersIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.8 19.5c.5-3 2.6-4.8 5.2-4.8s4.7 1.8 5.2 4.8" />
      <path d="M16 5.4a3 3 0 0 1 0 5.6" />
      <path d="M17.4 14.8c1.7.5 2.8 1.9 3.1 4" />
    </Icon>
  );
}

export function ChatIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20.5 11.4c0 4-3.8 7.2-8.5 7.2-1 0-2-.1-2.9-.4l-4.6 2 1.3-4A6.9 6.9 0 0 1 3.5 11.4c0-4 3.8-7.2 8.5-7.2s8.5 3.2 8.5 7.2Z" />
      <path d="M8.4 11.4h.01M12 11.4h.01M15.6 11.4h.01" strokeWidth="2.4" />
    </Icon>
  );
}

export function RiskIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3.5 5 6.6v5.2c0 4 2.9 7 7 8.7 4.1-1.7 7-4.7 7-8.7V6.6L12 3.5Z" />
      <path d="M12 8.6v3.8M12 15.8h.01" strokeWidth="2" />
    </Icon>
  );
}

export function BookIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 5.2A1.7 1.7 0 0 1 5.7 3.5H11v17H5.7A1.7 1.7 0 0 1 4 18.8V5.2Z" />
      <path d="M20 5.2a1.7 1.7 0 0 0-1.7-1.7H13v17h5.3a1.7 1.7 0 0 0 1.7-1.5V5.2Z" />
    </Icon>
  );
}

export function LogoutIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9.5 4.5H6.3A1.8 1.8 0 0 0 4.5 6.3v11.4a1.8 1.8 0 0 0 1.8 1.8h3.2" />
      <path d="M15 8.5 19 12l-4 3.5M19 12H9.5" />
    </Icon>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.3-5.4" />
      <path d="M19.5 4.5V9H15" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="10.8" cy="10.8" r="6.3" />
      <path d="m15.6 15.6 3.9 3.9" />
    </Icon>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M19 12H5M10.5 6.5 5 12l5.5 5.5" />
    </Icon>
  );
}

export function ArrowUpRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M7 17 17 7M9 7h8v8" />
    </Icon>
  );
}

export function ClockIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.2" />
      <path d="M12 7.5V12l3 1.8" />
    </Icon>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3.8c.7 4.2 2 5.5 6.2 6.2-4.2.7-5.5 2-6.2 6.2-.7-4.2-2-5.5-6.2-6.2 4.2-.7 5.5-2 6.2-6.2Z" />
      <path d="M18.5 15.5c.3 1.8.9 2.4 2.7 2.7-1.8.3-2.4.9-2.7 2.7-.3-1.8-.9-2.4-2.7-2.7 1.8-.3 2.4-.9 2.7-2.7Z" />
    </Icon>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m5 12.5 4.2 4.2L19 7" />
    </Icon>
  );
}

export function LogoMark(props: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path
        d="M4.5 9.6 12 5.4l7.5 4.2"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 15.2 12 10.8l8 4.4-8 4.4-8-4.4Z"
        fill="currentColor"
      />
    </svg>
  );
}
