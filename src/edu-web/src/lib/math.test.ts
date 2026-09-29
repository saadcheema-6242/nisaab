import { describe, expect, it } from 'vitest'
import { normalizeMath } from './math'

const raw = String.raw

describe('normalizeMath', () => {
  it('makes doubled LaTeX backslashes single (flashcard screenshot)', () => {
    const stored = raw`Horizontal position: $x = (v_i \\cos\\theta)t$ Vertical position: $y = (v_i \\sin\\theta)t - \\frac12gt^2$ in meters ($\\text{m}$).`
    expect(normalizeMath(stored)).toBe(
      raw`Horizontal position: $$x = (v_i \cos\theta)t$$ Vertical position: $$y = (v_i \sin\theta)t - \frac12gt^2$$ in meters ($$\text{m}$$).`,
    )
  })

  it('wraps formulas written without delimiters (answer screenshot)', () => {
    const stored = raw`At \\theta = 45^\\circ: H = \\frac{v_i^2 \\sin^2(45^\\circ)}{2g} = \\frac{v_i^2}{4g} Dividing the equations: $\\frac{R}{H} = 4 \\implies R = 4H$.`
    expect(normalizeMath(stored)).toBe(
      raw`At $$\theta = 45^\circ: H = \frac{v_i^2 \sin^2(45^\circ)}{2g} = \frac{v_i^2}{4g}$$ Dividing the equations: $$\frac{R}{H} = 4 \implies R = 4H$$.`,
    )
  })

  it('wraps a formula inside Roman Urdu text', () => {
    expect(normalizeMath(raw`Roman Urdu: 45^\\circ par range 4 guna hoti hai.`)).toBe(
      raw`Roman Urdu: $$45^\circ$$ par range 4 guna hoti hai.`,
    )
  })

  it('keeps correct math and plain text unchanged in meaning', () => {
    expect(normalizeMath(raw`Range is $R = \frac{v^2 \sin 2\theta}{g}$ at launch.`)).toBe(
      raw`Range is $$R = \frac{v^2 \sin 2\theta}{g}$$ at launch.`,
    )
    expect(normalizeMath('speed = distance / time, costs $ 5 and $10')).toBe(
      'speed = distance / time, costs $ 5 and $10',
    )
    expect(normalizeMath(raw`Use \(v = u + at\) then \[s = ut\] done`)).toBe(
      'Use $$v = u + at$$ then \n$$\ns = ut\n$$\n done',
    )
  })

  it('keeps list markers, line breaks and code', () => {
    expect(normalizeMath(raw`- H = \frac{v^2}{2g}`)).toBe(raw`- $$H = \frac{v^2}{2g}$$`)
    expect(normalizeMath(raw`$$\begin{aligned} a &= b \\ c &= d \end{aligned}$$`)).toBe(
      raw`$$\begin{aligned} a &= b \\ c &= d \end{aligned}$$`,
    )
    expect(normalizeMath(raw`Run \`x_1 = \\frac\` in code`)).toBe(raw`Run \`x_1 = \\frac\` in code`)
  })

  it('produces formulas that KaTeX can render', async () => {
    const katex = (await import('katex')).default
    await import('katex/contrib/mhchem')
    const samples = [
      raw`Horizontal position: $x = (v_i \\cos\\theta)t$ and $y = (v_i \\sin\\theta)t - \\frac12gt^2$ ($\\text{m}$).`,
      raw`At \\theta = 45^\\circ: H = \\frac{v_i^2 \\sin^2(45^\\circ)}{2g} = \\frac{v_i^2}{4g} Dividing: $\\frac{R}{H} = 4 \\implies R = 4H$.`,
      raw`Burning: $\\ce{CH4 + 2O2 -> CO2 + 2H2O}$`,
    ]
    for (const sample of samples) {
      const formulas = normalizeMath(sample).split('$$').filter((_, i) => i % 2 === 1)
      expect(formulas.length).toBeGreaterThan(0)
      for (const formula of formulas) {
        expect(() => katex.renderToString(formula, { throwOnError: true })).not.toThrow()
      }
    }
  })

  it('wraps a subscript variable mentioned in a sentence', () => {
    expect(normalizeMath('where v_i is the initial velocity')).toBe(
      'where $$v_i$$ is the initial velocity',
    )
  })
})
