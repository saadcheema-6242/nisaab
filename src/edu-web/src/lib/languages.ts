// Languages the tutor explains in. Formulas and technical terms stay in
// English in every mode, because FSc science papers are answered in English.
export const explanationLanguages = [
  { code: 'en', name: 'English', hint: 'Explanations in English' },
  { code: 'ur-Latn', name: 'Roman Urdu', hint: 'e.g. "Velocity ka matlab hai..."' },
  { code: 'ur', name: 'اردو (Urdu)', hint: 'Urdu script, terms in English' },
] as const

export type ExplanationLanguage = (typeof explanationLanguages)[number]['code']

export const languageName = (code: string) =>
  explanationLanguages.find((l) => l.code === code)?.name ?? code
