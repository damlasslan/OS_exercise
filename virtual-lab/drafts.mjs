// Pure helpers for resolving draft conflicts between two devices or tabs.
// base: the server draft this device last saw; local: this device's unsaved draft; server: the newer server draft.
// Fields edited only on this device take the local text, fields edited only elsewhere keep the server text,
// and fields edited in both places keep both texts so that nothing is lost.
export const OTHER_COPY_MARKER = '--- Text saved from another device or tab ---';

export function mergeDrafts(base, local, server) {
  const original = base || {}, mine = local || {}, theirs = server || {};
  const merged = { ...theirs }, conflicts = [];
  for (const key of new Set([...Object.keys(mine), ...Object.keys(original)])) {
    const ours = mine[key] ?? '', before = original[key] ?? '', other = theirs[key] ?? '';
    if (ours === before || ours === other) continue;
    if (other !== before && other !== '') {
      conflicts.push(key);
      merged[key] = ours + '\n\n' + OTHER_COPY_MARKER + '\n' + other;
    } else {
      merged[key] = ours;
    }
  }
  return { merged, conflicts };
}
