import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import css from 'highlight.js/lib/languages/css'
import go from 'highlight.js/lib/languages/go'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import kotlin from 'highlight.js/lib/languages/kotlin'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import rust from 'highlight.js/lib/languages/rust'
import sql from 'highlight.js/lib/languages/sql'
import swift from 'highlight.js/lib/languages/swift'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'
import katex from 'katex'
import { marked } from 'marked'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('css', css)
hljs.registerLanguage('go', go)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('kotlin', kotlin)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('swift', swift)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('yaml', yaml)

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
