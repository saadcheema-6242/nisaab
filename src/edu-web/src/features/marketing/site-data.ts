/**
 * Content for the public site. Kept in one place so the pages stay about
 * layout and the numbers stay honest: these are the real Part 1 figures.
 */

export const nav = [
  { to: '/', label: 'Home' },
  { to: '/features', label: 'Features' },
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
] as const

/** Class XI, all three groups. Counts match the seeded curriculum. */
export const subjects = [
  { code: 'PHY', name: 'Physics', slos: 193, examined: 150, colour: '#38BDF8' },
  { code: 'CHEM', name: 'Chemistry', slos: 329, examined: 217, colour: '#34D399' },
  { code: 'BIO', name: 'Biology', slos: 246, examined: 161, colour: '#FB7185' },
  { code: 'MATH', name: 'Mathematics', slos: 79, examined: 61, colour: '#A78BFA' },
  { code: 'CS', name: 'Computer Science', slos: 22, examined: 22, colour: '#FBBF24' },
] as const

export const totalSlos = subjects.reduce((n, s) => n + s.slos, 0)
export const totalExamined = subjects.reduce((n, s) => n + s.examined, 0)

export const stats = [
  { value: totalSlos, label: 'learning outcomes', detail: 'the whole FSc Part 1 syllabus' },
  { value: totalExamined, label: 'examinable SLOs', detail: 'the ones that carry marks' },
  { value: 34, label: 'domains', detail: 'across five subjects' },
  { value: 4000, label: 'practice questions', suffix: '+', detail: 'MCQs, short and long answers' },
] as const

export const features = [
  {
    slug: 'tutor',
    title: 'A tutor that knows your syllabus',
    blurb:
      'Ask anything and the answer comes back tied to the FBISE learning outcome it belongs to, in the depth your paper expects.',
  },
  {
    slug: 'syllabus',
    title: 'The syllabus, outcome by outcome',
    blurb:
      'Every SLO in Physics, Chemistry, Biology, Maths and Computer Science, with your progress marked on each one.',
  },
  {
    slug: 'quizzes',
    title: 'Practice built from the real pattern',
    blurb:
      'MCQs, short questions and long questions generated against the outcome you are weakest on, not at random.',
  },
  {
    slug: 'papers',
    title: 'Whole papers in the 2026 pattern',
    blurb:
      'Section A, B and C exactly as FBISE sets them, timed, marked and explained question by question.',
  },
  {
    slug: 'revision',
    title: 'Flashcards and mind maps',
    blurb:
      'Turn any topic into cards you can drill or a map you can see, then export them to print or share.',
  },
  {
    slug: 'marking',
    title: 'Marking that shows the marks',
    blurb:
      'Write an answer the way you would in the exam and get it back marked against the outcome, point by point.',
  },
] as const

/** Section A/B/C as FBISE sets the 2026 paper (Maths carries 100). */
export const paperPattern = [
  { section: 'A', title: 'Multiple choice', detail: '56 MCQs + 6 stimulus sets', marks: 40 },
  { section: 'B', title: 'Short questions', detail: '7 questions, 4 marks each', marks: 28 },
  { section: 'C', title: 'Extended response', detail: '2 questions, 6 marks each', marks: 12 },
] as const

export const languages = [
  { code: 'en', name: 'English', sample: 'Velocity is the rate of change of displacement.' },
  { code: 'ur-Latn', name: 'Roman Urdu', sample: 'Velocity ka matlab hai displacement ke change ki rate.' },
  { code: 'ur', name: 'اردو', sample: 'ویلاسٹی سے مراد ڈسپلیسمنٹ کی تبدیلی کی شرح ہے۔' },
] as const

export const team = [
  { name: 'Muhammad Saad Cheema', role: 'Development' },
  { name: 'Hashir Naveed', role: 'User interface design' },
  { name: 'Fatin Khan Jadoon', role: 'Presentation' },
] as const

export const supervisor = 'Prof. Muhammad Tashfeen Qamar'
export const college = 'Islamabad Model College for Boys, G-10/4'

/** The contact form composes a mailto: to this address. */
export const contactEmail = 'nisaab.imcb@gmail.com'
