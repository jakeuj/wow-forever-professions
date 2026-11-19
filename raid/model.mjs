export const groups = ['common', 'tank', 'healer', 'damage'];

export function mergeItems(rows) {
  const items = new Map();
  for (const row of rows) {
    const stored = items.get(row.id || row.name);
    items.set(row.id || row.name, { ...row, quantity: row.quantity + (stored?.quantity || 0) });
  }
  return [...items.values()];
}

export function verifyPlan(data) {
  const title = data?.title;
  if (data?.schema !== 1 || typeof title !== 'string' || !title.trim() || title.length > 60) {
    throw new Error('分享連結的清單格式有誤。');
  }
  const plan = { schema: 1, title };
  for (const group of groups) {
    const rows = data[group];
    if (!Array.isArray(rows) || rows.length > 20) throw new Error('每組最多可放 20 個品項。');
    if (rows.some(row => !row || typeof row.name !== 'string' || !row.name.trim()
      || row.name.length > 75 || /[\r\n]/u.test(row.name) || (row.id !== null && (!Number.isSafeInteger(row.id) || row.id <= 0))
      || !Number.isSafeInteger(row.quantity) || row.quantity < 1 || row.quantity > 9999)) {
      throw new Error('有品項的名稱或數量有誤。');
    }
    plan[group] = rows.map(({ id, name, quantity }) => ({ id, name, quantity }));
  }
  if (!groups.some(group => plan[group].length)) throw new Error('請至少加入一項備戰物品。');
  return plan;
}
