export type Locale = "zh-CN" | "en-US";

export type MessageValues = Record<string, string | number>;

export type MessageBundle = Record<Locale, Record<string, string>>;
