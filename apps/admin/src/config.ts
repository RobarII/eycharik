/**
 * Values that belong to the deployment, not to the code.
 *
 * Anything here must be true for the cabinet to make sense; a new scenario, a new tenant name or a
 * new role must be added to this file and nowhere else. Facts that the API owns — counts, windows,
 * capability lists — are never duplicated here.
 */
export const TENANT = {
  name: "ПОЛИПЛАСТИК",
  subtitle: "Онбординг в MAX",
} as const;

/** Scenario ids come from `apps/api/onboarding/scenarios/`; an unknown id prints as-is. */
export const SCENARIO_LABELS: Record<string, string> = {
  onboarding_default: "Офис",
  onboarding_plant: "Завод (ГТП)",
};

export const ROLE_LABELS: Record<string, string> = {
  recruiter: "Рекрутёр",
  manager: "Руководитель подразделения",
  hr_admin: "HR-администратор",
};

/** Channel ids come from `Channel` in the API; an unknown one prints as-is. */
export const CHANNEL_LABELS: Record<string, string> = {
  max: "MAX",
  telegram: "Telegram",
  vk: "ВКонтакте",
};

/** How often each screen re-reads the API. One place, so the numbers cannot drift apart. */
export const REFRESH = {
  overview: 30_000,
  runs: 15_000,
  questions: 15_000,
  digest: 30_000,
  run: 15_000,
  knowledge: 30_000,
  extraction: 2_000,
} as const;
