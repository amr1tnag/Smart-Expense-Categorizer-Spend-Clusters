import type { CategoryId } from "./types";

// Fixed order = fixed color slot. Color follows the category, never its rank,
// so a filter or a re-sort never repaints anything. Order is also the stacking
// order, which is what the palette's adjacent-pair validation assumes.
export const CATEGORY_ORDER: CategoryId[] = [
  "travel",
  "food",
  "shopping",
  "bills",
  "entertainment",
  "health",
  "rent",
  "other",
];

export const CATEGORY_LABEL: Record<CategoryId, string> = {
  travel: "Travel",
  food: "Food",
  shopping: "Shopping",
  bills: "Bills",
  entertainment: "Entertainment",
  health: "Health",
  rent: "Rent",
  other: "Other",
};

export function isCategory(value: string): value is CategoryId {
  return (CATEGORY_ORDER as string[]).includes(value);
}

/** CSS color for a category; the values live in globals.css so dark mode swaps in one place. */
export function categoryColor(id: string): string {
  return `var(--cat-${isCategory(id) ? id : "other"})`;
}

export function categoryLabel(id: string): string {
  return isCategory(id) ? CATEGORY_LABEL[id] : id;
}
