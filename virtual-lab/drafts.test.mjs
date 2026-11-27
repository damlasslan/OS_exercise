import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeDrafts, OTHER_COPY_MARKER } from './drafts.mjs';

test('edits to different fields on two devices are both kept', () => {
  const base = { architecture: 'A' };
  const local = { architecture: 'A', cpuCorrection: 'edited in tab one' };
  const server = { architecture: 'A', processes: 'edited in tab two' };
  const { merged, conflicts } = mergeDrafts(base, local, server);
  assert.deepEqual(merged, { architecture: 'A', processes: 'edited in tab two', cpuCorrection: 'edited in tab one' });
  assert.deepEqual(conflicts, []);
});

test('a field changed on both devices keeps both texts', () => {
  const { merged, conflicts } = mergeDrafts({ evaluation: 'old' }, { evaluation: 'mine' }, { evaluation: 'theirs' });
  assert.deepEqual(conflicts, ['evaluation']);
  assert.equal(merged.evaluation, 'mine\n\n' + OTHER_COPY_MARKER + '\ntheirs');
});

test('fields untouched on this device keep the newer server text', () => {
  const { merged } = mergeDrafts({ processes: 'v1' }, { processes: 'v1' }, { processes: 'v2' });
  assert.equal(merged.processes, 'v2');
});

test('deleting text on this device is applied when the server did not change it', () => {
  const { merged, conflicts } = mergeDrafts({ evaluation: 'draft' }, { evaluation: '' }, { evaluation: 'draft' });
  assert.equal(merged.evaluation, '');
  assert.deepEqual(conflicts, []);
});

test('an older local copy without a base never discards server text', () => {
  const { merged, conflicts } = mergeDrafts(undefined, { architecture: 'local' }, { architecture: 'server', processes: 'server only' });
  assert.deepEqual(conflicts, ['architecture']);
  assert.ok(merged.architecture.includes('local') && merged.architecture.includes('server'));
  assert.equal(merged.processes, 'server only');
});
