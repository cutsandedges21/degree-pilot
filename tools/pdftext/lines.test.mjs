import assert from 'node:assert/strict'
import test from 'node:test'
import { itemsToLines } from './lines.mjs'

const item = (str, x, y, width, height = 10) => ({ str, transform: [height, 0, 0, height, x, y], width })

test('orders lines top to bottom and items left to right', () => {
  const lines = itemsToLines([item('world', 37, 700, 25), item('second', 10, 680, 30), item('hello', 10, 700, 25)])
  assert.deepEqual(lines, ['hello world', 'second'])
})

test('wide gaps become tabs, narrow gaps spaces, touching items nothing', () => {
  const lines = itemsToLines([item('A', 0, 0, 10), item('B', 10.5, 0, 10), item('C', 23, 0, 10), item('D', 50, 0, 10)])
  assert.deepEqual(lines, ['AB C\tD'])
})

test('skips whitespace-only items and keeps a slightly shifted item on its line', () => {
  assert.deepEqual(itemsToLines([item('x', 0, 100, 5), item('  ', 5, 100, 5), item('y', 7, 102, 5)]), ['x y'])
})
