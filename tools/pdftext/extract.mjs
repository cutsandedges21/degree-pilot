// Usage: node tools/pdftext/extract.mjs <file.pdf>
// Prints the text, one line per PDF line. Exits 2 if the PDF has no text layer (a scan).
import { readFile } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { itemsToLines } from './lines.mjs'

GlobalWorkerOptions.workerSrc = import.meta.resolve('pdfjs-dist/legacy/build/pdf.worker.mjs')

export async function pdfToText(data) {
  // pdf.js 6 frees a document through its loading task, not the document itself.
  const task = getDocument({ data, verbosity: 0, isEvalSupported: false })
  try {
    const doc = await task.promise
    const pages = []
    for (let number = 1; number <= doc.numPages; number++) {
      const page = await doc.getPage(number)
      const content = await page.getTextContent()
      pages.push(itemsToLines(content.items).join('\n'))
    }
    return pages.filter((page) => page).join('\n')
  } finally {
    await task.destroy()
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const path = process.argv[2]
  if (!path) {
    console.error('usage: node extract.mjs <file.pdf>')
    process.exit(1)
  }
  const text = await pdfToText(new Uint8Array(await readFile(path)))
  if (!text.trim()) {
    console.error('no text layer (a scanned PDF?)')
    process.exit(2)
  }
  process.stdout.write(text + '\n')
}
