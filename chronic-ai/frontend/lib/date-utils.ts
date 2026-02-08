type LocaleLike = string | { code?: string } | undefined;

type FormatOptions = {
  locale?: LocaleLike;
};

type WeekOptions = {
  locale?: LocaleLike;
};

const DAY_MS = 24 * 60 * 60 * 1000;

const VI_WEEKDAY_SHORT = ["CN", "Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7"];
const VI_WEEKDAY_LONG = [
  "Chủ nhật",
  "Thứ hai",
  "Thứ ba",
  "Thứ tư",
  "Thứ năm",
  "Thứ sáu",
  "Thứ bảy",
];
const VI_MONTH_LONG = [
  "tháng 1",
  "tháng 2",
  "tháng 3",
  "tháng 4",
  "tháng 5",
  "tháng 6",
  "tháng 7",
  "tháng 8",
  "tháng 9",
  "tháng 10",
  "tháng 11",
  "tháng 12",
];
const VI_MONTH_SHORT = ["thg 1", "thg 2", "thg 3", "thg 4", "thg 5", "thg 6", "thg 7", "thg 8", "thg 9", "thg 10", "thg 11", "thg 12"];

export const vi = "vi-VN";

const pad2 = (value: number): string => String(value).padStart(2, "0");

const startOfDay = (date: Date): Date => {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
};

const normalizeLocale = (locale?: LocaleLike): string => {
  if (!locale) return vi;
  if (typeof locale === "string") return locale;
  return locale.code ?? vi;
};

export function format(date: Date, pattern: string, options?: FormatOptions): string {
  const locale = normalizeLocale(options?.locale);
  const day = date.getDate();
  const monthIdx = date.getMonth();
  const year = date.getFullYear();
  const weekday = date.getDay();
  const isVietnamese = locale.toLowerCase().startsWith("vi");

  switch (pattern) {
    case "yyyy-MM-dd":
      return `${year}-${pad2(monthIdx + 1)}-${pad2(day)}`;
    case "dd/MM/yyyy":
      return `${pad2(day)}/${pad2(monthIdx + 1)}/${year}`;
    case "dd/MM":
      return `${pad2(day)}/${pad2(monthIdx + 1)}`;
    case "d":
      return String(day);
    case "EEE":
      return isVietnamese ? VI_WEEKDAY_SHORT[weekday] : new Intl.DateTimeFormat(locale, { weekday: "short" }).format(date);
    case "EEEE, d MMMM yyyy":
      if (isVietnamese) return `${VI_WEEKDAY_LONG[weekday]}, ${day} ${VI_MONTH_LONG[monthIdx]} ${year}`;
      return new Intl.DateTimeFormat(locale, {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      }).format(date);
    case "d MMM":
      if (isVietnamese) return `${day} ${VI_MONTH_SHORT[monthIdx]}`;
      return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short" }).format(date);
    case "d MMMM yyyy":
      if (isVietnamese) return `${day} ${VI_MONTH_LONG[monthIdx]} ${year}`;
      return new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric" }).format(date);
    case "MMMM yyyy":
      if (isVietnamese) return `${VI_MONTH_LONG[monthIdx]} ${year}`;
      return new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(date);
    default:
      return new Intl.DateTimeFormat(locale).format(date);
  }
}

export function addDays(date: Date, amount: number): Date {
  return new Date(date.getTime() + amount * DAY_MS);
}

export function addMonths(date: Date, amount: number): Date {
  const d = new Date(date);
  d.setMonth(d.getMonth() + amount);
  return d;
}

export function subMonths(date: Date, amount: number): Date {
  return addMonths(date, -amount);
}

export function startOfWeek(date: Date, _options?: WeekOptions): Date {
  const d = startOfDay(date);
  // Monday-based week, aligned with Vietnamese calendar usage.
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

export function endOfWeek(date: Date, options?: WeekOptions): Date {
  return addDays(startOfWeek(date, options), 6);
}

export function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

export function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

export function eachDayOfInterval(interval: { start: Date; end: Date }): Date[] {
  const start = startOfDay(interval.start);
  const end = startOfDay(interval.end);
  const days: Date[] = [];
  for (let current = start; current.getTime() <= end.getTime(); current = addDays(current, 1)) {
    days.push(new Date(current));
  }
  return days;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function isSameMonth(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}
