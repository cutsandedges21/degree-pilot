import assert from 'node:assert/strict'
import test from 'node:test'
import { pdfToText } from './extract.mjs'

function makePdf(lines) {
  const content = lines.map(({ x, y, text }) => `BT /F1 12 Tf ${x} ${y} Td (${text}) Tj ET`).join('\n')
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  let pdf = '%PDF-1.4\n'
  const offsets = []
  objects.forEach((body, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`
  })
  const xref = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return new TextEncoder().encode(pdf)
}

test('keeps table columns apart with tabs', async () => {
  const pdf = makePdf([
    { x: 72, y: 720, text: 'ECON 201' }, { x: 200, y: 720, text: 'Intermediate Microeconomics' }, { x: 450, y: 720, text: 'A-' },
    { x: 72, y: 700, text: 'MATH 151' }, { x: 200, y: 700, text: 'Calculus I' }, { x: 450, y: 700, text: 'B+' },
  ])
  assert.equal(await pdfToText(pdf), 'ECON 201\tIntermediate Microeconomics\tA-\nMATH 151\tCalculus I\tB+')
})

test('a PDF with no text gives an empty string', async () => {
  assert.equal(await pdfToText(makePdf([])), '')
})
