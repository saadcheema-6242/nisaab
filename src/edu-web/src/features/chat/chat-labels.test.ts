import { describe, expect, it } from 'vitest'
import { chatLang, errorLabel, stageLabel, toolLabels } from './chat-labels'

describe('chatLang', () => {
  it('maps the three explanation languages, anything else to English', () => {
    expect(chatLang('ur')).toBe('ur')
    expect(chatLang('ur-Latn')).toBe('ur-Latn')
    expect(chatLang('en')).toBe('en')
    expect(chatLang(null)).toBe('en')
    expect(chatLang('fr')).toBe('en')
  })
})

describe('toolLabels', () => {
  it('speaks the student’s language for the tutor’s own tools', () => {
    expect(toolLabels('practice_quiz', 'en').running).toBe('Preparing your quiz…')
    expect(toolLabels('practice_quiz', 'ur-Latn').running).toBe(
      'Quiz tayyar kar raha hoon…',
    )
    expect(toolLabels('practice_quiz', 'ur').done).toBe('آپ کا کوئز تیار ہے')
  })

  it('has every language for every known tool, and never an empty string', () => {
    const tools = [
      'search_project_documents',
      'search_web',
      'find_syllabus_slos',
      'ask_practice_questions',
      'practice_quiz',
      'practice_flashcards',
      'practice_mind_map',
      'practice_paper',
      'draw_diagram',
    ]
    for (const tool of tools)
      for (const lang of ['en', 'ur-Latn', 'ur'] as const) {
        const { running, done } = toolLabels(tool, lang)
        expect(running.trim(), `${tool} ${lang}`).not.toBe('')
        expect(done.trim(), `${tool} ${lang}`).not.toBe('')
      }
  })

  it('falls back for a tool with no wording of its own', () => {
    expect(toolLabels('note_create', 'en').running).toBe('Making your note…')
    expect(toolLabels('note_create', 'ur-Latn').running).toBe(
      'Kaam kar raha hoon…',
    )
    expect(toolLabels('something_odd', 'ur').done).toBe('ہو گیا')
  })
})

describe('stageLabel and errorLabel', () => {
  it('cover thinking, writing, the long wait and errors', () => {
    expect(stageLabel('thinking', 'en')).toBe('Thinking…')
    expect(stageLabel('thinking', 'ur-Latn')).toBe('Soch raha hoon…')
    expect(stageLabel('writing', 'ur')).toBe('جواب لکھ رہا ہوں…')
    expect(stageLabel('slow', 'ur-Latn')).toContain('waqt')
    expect(errorLabel('ur-Latn')).toContain('dobara')
  })
})
