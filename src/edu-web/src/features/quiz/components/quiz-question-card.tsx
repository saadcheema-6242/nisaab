import { Result, useAtomSet, useAtomValue } from '@effect-atom/atom-react'
import { Option } from 'effect'
import { CheckCircle, XCircle } from 'lucide-react'
import {
  currentQuestionAtom,
  quizDetailStateAtom,
  setSelectedAnswerAtom,
} from '@/data-acess/quiz-detail-state'
import { MathText } from '@/components/math-text'
import { CognitiveBadge } from '@/features/syllabus/cognitive-badge'
import { ImageCredit } from '@/components/image-credit'

type QuizQuestionCardProps = {
  quizId: string
  projectId: string
}

export const QuizQuestionCard = ({
  quizId,
  projectId,
}: QuizQuestionCardProps) => {
  const stateResult = useAtomValue(quizDetailStateAtom(quizId))
  const currentQuestionResult = useAtomValue(
    currentQuestionAtom(`${projectId}:${quizId}`),
  )

  const setSelectedAnswer = useAtomSet(setSelectedAnswerAtom, {
    mode: 'promise',
  })

  const state = Option.isSome(stateResult) ? stateResult.value : null
  if (!state) return null

  const currentQuestion = Result.isSuccess(currentQuestionResult)
    ? currentQuestionResult.value
    : null
  if (!currentQuestion) return null

  const selected = state.selectedByQuestionId[currentQuestion.id]
  const showResults = state.showResults

  const handleSelect = async (option: 'A' | 'B' | 'C' | 'D') => {
    if (showResults) return
    await setSelectedAnswer({
      quizId,
      questionId: currentQuestion.id,
      option,
    })
  }

  const options: Array<{
    key: 'A' | 'B' | 'C' | 'D'
    label: string
  }> = [
    { key: 'A', label: currentQuestion.option_a },
    { key: 'B', label: currentQuestion.option_b },
    { key: 'C', label: currentQuestion.option_c },
    { key: 'D', label: currentQuestion.option_d },
  ]

  const getAnswerClasses = (option: 'A' | 'B' | 'C' | 'D') => {
    if (!showResults) {
      return selected === option
        ? 'bg-primary/10 border-primary'
        : 'bg-card border-border'
    }
    const isSelected = selected === option
    const isCorrect = currentQuestion.correct_option === option
    if (isCorrect) return 'bg-green-50 border-green-500 text-green-900'
    // isCorrect is already false here, so selected means selected-and-wrong
    if (isSelected) return 'bg-red-50 border-red-500 text-red-900'
    return 'bg-muted/50 border-border'
  }

  // The links come back keyed by lower-case letter; the buttons use A-D
  const optionImage = (option: string) => {
    const links = currentQuestion.option_image_urls
    if (!links) return null
    const url = links[option.toLowerCase()]
    return typeof url === 'string' && url ? url : null
  }

  const getOptionText = (option: string) => {
    if (option === 'A') return currentQuestion.option_a
    if (option === 'B') return currentQuestion.option_b
    if (option === 'C') return currentQuestion.option_c
    return currentQuestion.option_d
  }

  return (
    <div className="flex-1 flex items-center justify-center">
      <div className="w-full max-w-3xl">
        <div className="bg-card border rounded-xl shadow-lg p-12">
          <div className="space-y-10">
            <div>
              {/* What the question asks of the student - recall, explain or
                  apply. Shown before the question, because knowing which it is
                  changes how you read it. */}
              <CognitiveBadge
                level={currentQuestion.cognitive_level}
                showName
                className="mb-3"
              />
              <MathText className="text-lg font-medium leading-relaxed mb-6">
                {currentQuestion.question_text}
              </MathText>
              {/* Some questions cannot be asked in words: a circuit, a graph,
                  the forces on a body. The link is signed and short-lived. */}
              {currentQuestion.image_url && (
                <figure className="mb-6 w-full max-w-xl mx-auto">
                  <img
                    src={currentQuestion.image_url}
                    alt={currentQuestion.image_alt ?? 'Diagram for this question'}
                    className="w-full rounded-lg border bg-white"
                    loading="lazy"
                  />
                  {/* Naming the author, licence and source is a condition of
                      the licence the diagram was published under. */}
                  <figcaption className="mt-1">
                    <ImageCredit credit={currentQuestion.image_credit} />
                  </figcaption>
                </figure>
              )}
              {showResults && (
                <div className="flex items-center gap-2 mb-4">
                  {selected === currentQuestion.correct_option ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0" />
                      <span className="text-sm text-green-600 font-medium">
                        Correct
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-red-600 shrink-0" />
                      <span className="text-sm text-red-600 font-medium">
                        Incorrect
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="grid gap-3">
              {options.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => handleSelect(opt.key)}
                  disabled={showResults}
                  className={`text-left p-4 border rounded-lg transition-all ${
                    showResults
                      ? 'cursor-default'
                      : 'cursor-pointer hover:shadow-md'
                  } ${getAnswerClasses(opt.key)}`}
                >
                  <div className="flex gap-3">
                    <span className="font-semibold shrink-0">{opt.key}.</span>
                    <div className="min-w-0">
                      <MathText className="leading-relaxed">
                        {opt.label}
                      </MathText>
                      {/* Questions answered by choosing between pictures:
                          "which of these is benzene?" */}
                      {optionImage(opt.key) && (
                        <img
                          src={optionImage(opt.key)!}
                          alt={opt.label}
                          className="mt-2 w-full max-w-[14rem] rounded border bg-white"
                          loading="lazy"
                        />
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {showResults && (
              <div className="pt-4 space-y-2 border-t">
                <div className="text-sm">
                  <span className="text-muted-foreground">
                    Correct answer:{' '}
                  </span>
                  <div className="flex gap-1 font-semibold text-green-700">
                    <span>{currentQuestion.correct_option}.</span>
                    <MathText>
                      {getOptionText(currentQuestion.correct_option)}
                    </MathText>
                  </div>
                </div>
                {currentQuestion.explanation && (
                  <div className="text-sm text-muted-foreground leading-relaxed">
                    <span className="font-medium">Explanation: </span>
                    <MathText>{currentQuestion.explanation}</MathText>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
