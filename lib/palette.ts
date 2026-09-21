// Validated categorical palette (dark-surface steps), fixed hue order — see
// the dataviz skill's references/palette.md. Never cycle or reassign by rank.
export const CATEGORICAL: string[] = [
  "#3987e5", // 1 blue
  "#d95926", // 2 orange
  "#199e70", // 3 aqua
  "#c98500", // 4 yellow
  "#d55181", // 5 magenta
  "#008300", // 6 green
  "#9085e9", // 7 violet
  "#e66767", // 8 red
];

export const SEQUENTIAL_BLUE = "#3987e5";

export const INK = {
  primary: "#ffffff",
  secondary: "#c3c2b7",
  muted: "#898781",
  gridline: "#2c2c2a",
  baseline: "#383835",
};

export function colorForIndex(i: number): string {
  return CATEGORICAL[i % CATEGORICAL.length];
}
