import { en } from "./en";

export type Dict = typeof en;
export type Lang = "en" | "ru";
export type AlertKey = keyof Dict["alertNames"];
export type TriggerKey = keyof Dict["triggerNames"];
export type DictStringKey = { [K in keyof Dict]: Dict[K] extends string ? K : never }[keyof Dict];
