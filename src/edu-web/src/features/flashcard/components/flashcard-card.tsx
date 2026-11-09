import { useAtomValue } from '@effect-atom/atom-react'
import { Option } from 'effect'
import { Card } from '@/components/ui/card'
import { flashcardDetailStateAtom } from '@/features/flashcard/state/flashcard-detail-state'
import { MathText } from '@/components/math-text'

type FlashcardCardProps = {
  flashcardGroupId: string
  question: string
  answer: string
}

export const FlashcardCard = ({
  flashcardGroupId,
  question,
  answer,
}: FlashcardCardProps) => {
  const stateResult = useAtomValue(flashcardDetailStateAtom(flashcardGroupId))
  const state = Option.isSome(stateResult) ? stateResult.value : null
  const showAnswer = state?.showAnswer ?? false

  return (
    <div className="flex-1 flex items-center justify-center">
      <Card className="w-full max-w-3xl p-6 sm:p-12 min-h-[420px]">
        <div className="space-y-10">
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-2">
              Question
            </h3>
            <MathText className="text-lg leading-relaxed">{question}</MathText>
          </div>

          {showAnswer && (
            <div className="border-t pt-8">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">
                Answer
              </h3>
              <MathText className="text-lg leading-relaxed text-primary">
                {answer}
              </MathText>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
