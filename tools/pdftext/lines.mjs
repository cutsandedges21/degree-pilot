// pdf.js text items -> lines of text. Pure, so the browser app can reuse it unchanged.
// Items on the same baseline (within half their height) form one line, left to right.
// A gap wider than the text height becomes a tab, so table columns stay apart; a
// smaller visible gap becomes a space.

export function itemsToLines(items) {
  const rows = []
  for (const item of items) {
    if (!item.str || !item.str.trim()) continue
    const height = Math.abs(item.transform[3]) || item.height || 10
    const x = item.transform[4]
    const y = item.transform[5]
    let row = rows.find((candidate) => Math.abs(candidate.y - y) <= height / 2)
    if (!row) {
      row = { y, items: [] }
      rows.push(row)
    }
    row.items.push({ x, width: item.width, str: item.str, height })
  }
  rows.sort((a, b) => b.y - a.y) // PDF y grows upward
  return rows.map((row) => {
    row.items.sort((a, b) => a.x - b.x)
    let line = ''
    let end = null
    for (const piece of row.items) {
      if (end !== null) {
        const gap = piece.x - end
        line += gap > piece.height ? '\t' : gap > piece.height * 0.15 ? ' ' : ''
      }
      line += piece.str
      end = piece.x + piece.width
    }
    return line.replace(/[ \t]+$/, '')
  })
}
