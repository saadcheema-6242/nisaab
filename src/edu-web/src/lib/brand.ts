import { env } from '@/env'

// NISAAB (نصاب) is Urdu for "syllabus"; VITE_APP_TITLE can override the name
export const brand = {
  name: env.VITE_APP_TITLE ?? 'NISAAB',
  tagline: 'Your AI tutor for FBISE FSc: Physics, Chemistry, Biology and Maths',
  notice:
    'Aligned with the FBISE National Curriculum 2022-23. Not an official FBISE product.',
}
