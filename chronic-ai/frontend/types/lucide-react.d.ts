declare module "lucide-react" {
  import * as React from "react";

  export interface LucideProps extends React.SVGProps<SVGSVGElement> {
    color?: string;
    size?: string | number;
    strokeWidth?: string | number;
    absoluteStrokeWidth?: boolean;
  }

  export type LucideIcon = React.ForwardRefExoticComponent<
    LucideProps & React.RefAttributes<SVGSVGElement>
  >;

  export const icons: Record<string, LucideIcon>;
  export const createLucideIcon: (name: string, iconNode: unknown) => LucideIcon;

  export const Activity: LucideIcon;
  export const AlertCircle: LucideIcon;
  export const AlertTriangle: LucideIcon;
  export const ArrowLeft: LucideIcon;
  export const ArrowRight: LucideIcon;
  export const Bell: LucideIcon;
  export const Bot: LucideIcon;
  export const Calendar: LucideIcon;
  export const Check: LucideIcon;
  export const CheckCircle2: LucideIcon;
  export const ChevronDownIcon: LucideIcon;
  export const ChevronLeft: LucideIcon;
  export const ChevronLeftIcon: LucideIcon;
  export const ChevronRight: LucideIcon;
  export const ChevronRightIcon: LucideIcon;
  export const CircleIcon: LucideIcon;
  export const Clock: LucideIcon;
  export const Copy: LucideIcon;
  export const File: LucideIcon;
  export const FileText: LucideIcon;
  export const GripVerticalIcon: LucideIcon;
  export const Info: LucideIcon;
  export const LayoutDashboard: LucideIcon;
  export const Loader2: LucideIcon;
  export const LogOut: LucideIcon;
  export const Mail: LucideIcon;
  export const MessageSquare: LucideIcon;
  export const MinusIcon: LucideIcon;
  export const MoreHorizontal: LucideIcon;
  export const PanelLeftIcon: LucideIcon;
  export const Phone: LucideIcon;
  export const Pill: LucideIcon;
  export const Search: LucideIcon;
  export const SearchIcon: LucideIcon;
  export const Send: LucideIcon;
  export const Settings: LucideIcon;
  export const Sparkles: LucideIcon;
  export const Stethoscope: LucideIcon;
  export const TestTube: LucideIcon;
  export const TrendingUp: LucideIcon;
  export const Upload: LucideIcon;
  export const User: LucideIcon;
  export const UserPlus: LucideIcon;
  export const Users: LucideIcon;
  export const X: LucideIcon;
  export const XIcon: LucideIcon;
}
