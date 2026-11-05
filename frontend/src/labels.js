export const TYPE_LABELS = { functional: "Functional", non_functional: "Non-functional" };
export const CATEGORIES = ["performance", "security", "usability", "reliability", "maintainability", "other"];
export const KIND_LABELS = {
  vague_expression: "Vague expression",
  missing_measure: "Missing measure",
  unclear_actor: "Unclear actor",
  unspecified_behavior: "Unspecified behaviour",
  potential_contradiction: "Potential contradiction",
};
export const capitalize = (text) => (text ? text[0].toUpperCase() + text.slice(1) : "");
