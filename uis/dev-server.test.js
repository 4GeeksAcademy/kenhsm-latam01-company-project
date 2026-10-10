const test = require('node:test');
const assert = require('node:assert/strict');
const { getContentType } = require('./dev-server.js');

test('dev server sets JS content type for browser modules', () => {
  assert.equal(getContentType('main.js'), 'text/javascript; charset=utf-8');
  assert.equal(getContentType('styles.css'), 'text/css; charset=utf-8');
  assert.equal(getContentType('index.html'), 'text/html; charset=utf-8');
});
