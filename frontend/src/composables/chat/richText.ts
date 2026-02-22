import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import katex from 'katex'
import { marked } from 'marked'

export function renderRichText(raw: string): string {
  let text = raw || ''
  let counter = 0
  const mathMap: Record<string, { math: string; displayMode: boolean }> = {}

  const saveMath = (math: string, displayMode: boolean): string => {
    const id = `MATHPLACEHOLDER${counter++}END`
    mathMap[id] = { math, displayMode }
    return id
  }

  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => saveMath(m, true))
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => saveMath(m, true))
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => saveMath(m, false))
  text = text.replace(/(^|[^\\])\$([^$\n]+?)\$/g, (_, prefix, m) => prefix + saveMath(m, false))

  const renderer = new marked.Renderer()
  renderer.code = ({ text: codeText, lang }: { text: string; lang?: string }) => {
    const result = lang
      ? hljs.getLanguage(lang)
        ? hljs.highlight(codeText, { language: lang })
        : hljs.highlightAuto(codeText)
      : hljs.highlightAuto(codeText)

    const highlighted = result.value
    const copySvg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>'
    const checkSvg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'
    const langLabel = lang ? `<span class="code-lang">${lang}</span>` : ''

    return `<pre class="hljs-pre">${langLabel}<button class="code-copy-btn" title="复制代码"><span class="icon-copy">${copySvg}</span><span class="icon-check">${checkSvg}</span></button><code class="hljs">${highlighted}</code></pre>`
  }

  let parsedHtml = marked.parse(text, {
    breaks: true,
    gfm: true,
    renderer,
  }) as string

  parsedHtml = DOMPurify.sanitize(parsedHtml, {
    ALLOWED_TAGS: [
      'b',
      'i',
      'em',
      'strong',
      'a',
      'p',
      'br',
      'ul',
      'ol',
      'li',
      'span',
      'div',
      'code',
      'pre',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'blockquote',
      'img',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'hr',
      'del',
      's',
      'button',
      'svg',
      'rect',
      'path',
      'polyline',
    ],
    ALLOWED_ATTR: [
      'href',
      'title',
      'class',
      'style',
      'src',
      'alt',
      'target',
      'rel',
      'xmlns',
      'width',
      'height',
      'viewBox',
      'fill',
      'stroke',
      'stroke-width',
      'stroke-linecap',
      'stroke-linejoin',
      'x',
      'y',
      'rx',
      'ry',
      'd',
      'points',
    ],
  })

  for (const id in mathMap) {
    const { math, displayMode } = mathMap[id]
    try {
      const rendered = katex.renderToString(math, {
        displayMode,
        throwOnError: false,
      })
      parsedHtml = parsedHtml.replace(id, rendered)
    } catch {
      parsedHtml = parsedHtml.replace(id, '<span class="latex-error">[LaTeX 错误]</span>')
    }
  }

  return parsedHtml
}

export function handleCopyCode(event: MouseEvent) {
  const btn = (event.target as HTMLElement).closest('.code-copy-btn') as HTMLElement | null
  if (!btn) return

  const pre = btn.closest('pre')
  if (!pre) return

  const code = pre.querySelector('code')?.innerText ?? ''
  navigator.clipboard.writeText(code).then(() => {
    btn.classList.add('copied')
    setTimeout(() => btn.classList.remove('copied'), 1500)
  })
}
