/**
 * What the tutor says it is doing, in the language the student chose for the
 * subject. Formulas, SLO codes and technical terms stay in English everywhere,
 * as they do in the answers themselves.
 */

export type ChatLang = 'en' | 'ur-Latn' | 'ur'

export const chatLang = (code?: string | null): ChatLang =>
  code === 'ur' ? 'ur' : code === 'ur-Latn' ? 'ur-Latn' : 'en'

type Phrase = Record<ChatLang, string>

/** Stages the chat itself reports, between sending and the first word written. */
const STAGES: Record<'thinking' | 'writing' | 'slow', Phrase> = {
  thinking: {
    en: 'Thinking…',
    'ur-Latn': 'Soch raha hoon…',
    ur: 'سوچ رہا ہوں…',
  },
  writing: {
    en: 'Writing your answer…',
    'ur-Latn': 'Jawab likh raha hoon…',
    ur: 'جواب لکھ رہا ہوں…',
  },
  slow: {
    en: 'This one is taking a little longer…',
    'ur-Latn': 'Is mein thora waqt lag raha hai…',
    ur: 'اس میں تھوڑا وقت لگ رہا ہے…',
  },
}

export const stageLabel = (
  stage: keyof typeof STAGES,
  lang: ChatLang,
): string => STAGES[stage][lang]

export const errorLabel = (lang: ChatLang): string =>
  ({
    en: 'Something went wrong, please try again',
    'ur-Latn': 'Kuch ghalat ho gaya, dobara koshish karein',
    ur: 'کچھ غلط ہو گیا، دوبارہ کوشش کریں',
  })[lang]

export const openLabel = (lang: ChatLang): string =>
  ({ en: 'Open', 'ur-Latn': 'Kholein', ur: 'کھولیں' })[lang]

export type ToolLabels = { running: string; done: string }

const TOOLS: Record<string, Record<ChatLang, ToolLabels> | undefined> = {
  search_project_documents: {
    en: { running: 'Searching your documents…', done: 'Searched your documents' },
    'ur-Latn': {
      running: 'Aap ke documents mein dhoond raha hoon…',
      done: 'Documents dekh liye',
    },
    ur: { running: 'آپ کے دستاویزات دیکھ رہا ہوں…', done: 'دستاویزات دیکھ لیے' },
  },
  search_web: {
    en: { running: 'Searching the web…', done: 'Searched the web' },
    'ur-Latn': {
      running: 'Web par dhoond raha hoon…',
      done: 'Web par dekh liya',
    },
    ur: { running: 'ویب پر تلاش کر رہا ہوں…', done: 'ویب پر دیکھ لیا' },
  },
  find_syllabus_slos: {
    en: {
      running: 'Checking the FBISE syllabus…',
      done: 'Checked the FBISE syllabus',
    },
    'ur-Latn': {
      running: 'FBISE syllabus check kar raha hoon…',
      done: 'FBISE syllabus check kar liya',
    },
    ur: { running: 'FBISE سلیبس دیکھ رہا ہوں…', done: 'FBISE سلیبس دیکھ لیا' },
  },
  ask_practice_questions: {
    en: {
      running: 'Thinking about your practice…',
      done: 'A few quick questions first',
    },
    'ur-Latn': {
      running: 'Aap ki practice ke bare mein soch raha hoon…',
      done: 'Pehle chand chhote sawal',
    },
    ur: {
      running: 'آپ کی پریکٹس کے بارے میں سوچ رہا ہوں…',
      done: 'پہلے چند چھوٹے سوالات',
    },
  },
  practice_quiz: {
    en: { running: 'Preparing your quiz…', done: 'Your quiz is ready' },
    'ur-Latn': {
      running: 'Quiz tayyar kar raha hoon…',
      done: 'Aap ka quiz tayyar hai',
    },
    ur: { running: 'کوئز تیار کر رہا ہوں…', done: 'آپ کا کوئز تیار ہے' },
  },
  practice_flashcards: {
    en: {
      running: 'Preparing your flashcards…',
      done: 'Your flashcards are ready',
    },
    'ur-Latn': {
      running: 'Flashcards tayyar kar raha hoon…',
      done: 'Aap ke flashcards tayyar hain',
    },
    ur: {
      running: 'فلیش کارڈز تیار کر رہا ہوں…',
      done: 'آپ کے فلیش کارڈز تیار ہیں',
    },
  },
  practice_mind_map: {
    en: { running: 'Drawing your mind map…', done: 'Your mind map is ready' },
    'ur-Latn': {
      running: 'Mind map bana raha hoon…',
      done: 'Aap ka mind map tayyar hai',
    },
    ur: { running: 'مائنڈ میپ بنا رہا ہوں…', done: 'آپ کا مائنڈ میپ تیار ہے' },
  },
  practice_paper: {
    en: {
      running: 'Setting your practice paper…',
      done: 'Your practice paper is set',
    },
    'ur-Latn': {
      running: 'Aap ka paper tayyar kar raha hoon…',
      done: 'Aap ka paper tayyar hai',
    },
    ur: { running: 'آپ کا پیپر تیار کر رہا ہوں…', done: 'آپ کا پیپر تیار ہے' },
  },
}

const GENERIC: Record<ChatLang, ToolLabels> = {
  en: { running: 'Working on it…', done: 'Done' },
  'ur-Latn': { running: 'Kaam kar raha hoon…', done: 'Ho gaya' },
  ur: { running: 'کام کر رہا ہوں…', done: 'ہو گیا' },
}

const ITEMS: Record<string, string> = {
  quiz: 'quiz',
  flashcards: 'flashcards',
  note: 'note',
  mindmap: 'mind map',
}

/** Friendly text for one of the tutor's tools; raw tool names mean nothing to students. */
export const toolLabels = (name: string, lang: ChatLang): ToolLabels => {
  const known = TOOLS[name]
  if (known) return known[lang]
  if (lang !== 'en') return GENERIC[lang]

  // English only: the tools the tutor rarely reaches for, named from the tool itself
  const [area, action = ''] = name.split(/_(.+)/)
  const item = ITEMS[area] ?? 'content'
  const plural = item.endsWith('s') ? item : `${item}s`
  if (action.startsWith('create'))
    return {
      running: `Making your ${item}…`,
      done: `${item.charAt(0).toUpperCase()}${item.slice(1)} ready`,
    }
  if (action.startsWith('delete'))
    return { running: `Deleting ${item}…`, done: `Deleted ${item}` }
  if (action.startsWith('update'))
    return { running: `Updating ${item}…`, done: `Updated ${item}` }
  return { running: `Looking at your ${plural}…`, done: `Checked your ${plural}` }
}
