export const professions = [
  { id: 'tailoring', name: '裁縫', mark: '裁', kind: 'craft' },
  { id: 'enchanting', name: '附魔', mark: '附', kind: 'craft' },
  { id: 'alchemy', name: '煉金術', mark: '煉', kind: 'craft' },
  { id: 'leatherworking', name: '製皮', mark: '皮', kind: 'craft' },
  { id: 'blacksmithing', name: '鍛造', mark: '鍛', kind: 'craft' },
  { id: 'engineering', name: '工程學', mark: '工', kind: 'craft' },
  { id: 'herbalism', name: '草藥學', kind: 'gather' },
  { id: 'skinning', name: '剝皮', kind: 'gather' },
  { id: 'mining', name: '採礦', kind: 'gather' },
];
export const crafting = professions.filter(p => p.kind === 'craft');
const mage = { classId: 'mage', name: '法師', seal: '法', role: '全帳號後勤', order: '優先建立', profs: ['tailoring', 'enchanting'], reason: '做包、布甲自用；裁縫裝備與可郵寄綠裝供應附魔材料。' };
const druid = { classId: 'druid', name: '德魯伊', seal: '德', role: '草藥與藥水', order: '第二隻副角', profs: ['herbalism', 'alchemy'], reason: '採草供煉金，製作藥水與轉化材料；也可先剝皮／採草再轉。' };
const hunter = { classId: 'hunter', name: '獵人', seal: '獵', role: '皮料與營地', order: '第三隻副角', profs: ['skinning', 'leatherworking'], reason: '打獸剝皮、製作皮甲與鎖甲，並負責製皮帳篷的用途。' };
const rogue = { classId: 'rogue', name: '盜賊', seal: '賊', role: '工程與工具', order: '第四隻副角', profs: ['mining', 'engineering'], reason: '礦料自供工程工具；增加控場與工具選擇。' };
const warrior = { classId: 'warrior', name: '戰士', seal: '戰', role: '武器與護甲', order: '長期工匠', profs: ['mining', 'blacksmithing'], reason: '採礦直接供應鍛造，製作自用武器與護甲。' };
const paladin = { classId: 'paladin', name: '聖騎士', seal: '聖', role: '保留既有投入', order: '現有主角', profs: ['mining', 'blacksmithing'], reason: '礦料直接供應武器與護甲製作；維持主角的採礦／鍛造。' };
export const plans = {
  crafting: {
    label: '雙採集主號＋雙製造小號', tag: 'PLAN A · 集中製造首選', title: '主號供材料，三位小號各練雙製造。',
    description: '德魯伊主號保留採草／剝皮；法師裁縫／附魔、獵人製皮／煉金、戰士鍛造／工程，把六項製造集中在三隻小號。盜賊負責採礦，第二格彈性保留。先從主號與法師起步，其餘角色逐步補齊。',
    note: '完整分工涵蓋九項專業，三位製造工匠各最多 6 點，合計 18 點。主號不用洗掉剝皮；材料需跨角色供應，小號仍須滿足製造升階條件。盜賊的第二格可留空或依玩法再選，不影響覆蓋。',
    rows: [
      { ...druid, order: '雙採集主號', role: '草藥與皮料', profs: ['herbalism', 'skinning'], reason: '主號長期保留雙採集，草藥與皮料供應獵人的煉金／製皮。' },
      { ...mage, order: '第一隻小號', role: '雙製造：布甲', reason: '裁縫／附魔集中同一隻，先做包與拆裝，再逐步完成兩項製造里程碑。' },
      { ...hunter, order: '雙製造小號', role: '雙製造：皮與草', profs: ['leatherworking', 'alchemy'], reason: '接收主號的皮料與草藥，製作皮／鎖甲、藥水與轉化材料。' },
      { ...warrior, order: '雙製造小號', role: '雙製造：礦料', profs: ['blacksmithing', 'engineering'], reason: '接收採礦角色的礦料，集中製作鍛造裝備與工程工具。' },
      { ...rogue, order: '採礦採集角', role: '礦料與彈性格', profs: ['mining'], flexibleSlot: true, reason: '礦料供應戰士。第二格可留空或另選採集；採集角也要能前往對應地圖。' },
    ],
  },
  gathering: {
    label: '雙採集後轉製造', tag: 'PLAN B · 分階段養成', title: '主號先雙採集，之後把剝皮換成煉金。',
    description: '先建立兩隻角色：德魯伊主號剝皮／採草，法師小號裁縫／附魔。其餘三位工匠之後再補；皮料留給獵人、草藥留作煉金，準備好再轉換。',
    note: '長期將德魯伊的剝皮換成煉金，保留採草。等獵人能持續供皮、煉金材料與升階條件準備好即可，不必硬等滿級。',
    startNote: '開局暫缺煉金，因此目前涵蓋 8 項專業、5 項製造。若永久保留雙採集，需另找角色學煉金，或讓另一位工匠改雙製造。',
    rows: [{ ...druid, order: '主號', reason: '長期保留採草，把剝皮換成煉金；材料與升階條件備妥後再轉。' }, { ...mage, order: '第一隻小號' }, { ...hunter, order: '後續：承接皮料' }, { ...warrior, order: '後續：鍛造' }, { ...rogue, order: '後續：工程' }],
  },
  balanced: {
    label: '直接全專業分工', tag: 'PLAN C · 長期分工', title: '直接搭配採集與製造，建立完整分工。',
    description: '適合想邊練等、邊製作裝備的玩家。法師負責裁縫／附魔，其餘製造各配一項採集，逐步建立五隻不同職業的工匠。',
    note: '採礦重複一次，分別支援鍛造與工程。已有聖騎士採礦／鍛造的玩家，也可參考第四版延續既有投入。',
    rows: [mage, druid, hunter, warrior, rogue],
  },
  paladin: {
    label: '聖騎士既有配置', tag: 'PLAN D · 既有角色延伸', title: '已有採礦／鍛造？讓聖騎士繼續擔任工匠。',
    description: '適合已學採礦／鍛造的聖騎士玩家。延續既有角色，再由法師提供裁縫／附魔，其他副角補上煉金、製皮與工程。',
    note: '採礦重複一次：鍛造與工程各有礦料需求。五種職業不重複，九項主要專業全部涵蓋。',
    rows: [paladin, mage, druid, hunter, { ...rogue, reason: '礦料自供工程工具，與聖騎士互補供應；增加控場與工具選擇。' }],
  },
};
export function getRows(planId, stage = 'final') {
  const plan = plans[planId] || plans.crafting;
  return plan.rows.map(row => planId === 'gathering' && stage === 'start' && row.classId === 'druid'
    ? { ...row, profs: ['skinning', 'herbalism'], role: '雙採集起家', reason: '剝皮與採草存材料；皮留給獵人、草藥留給未來的煉金。此階段沒有製造傳承點數。' }
    : row);
}
export function summarize(rows) {
  const ids = new Set(rows.flatMap(row => row.profs));
  const craftCharacters = rows.filter(row => row.profs.some(id => crafting.some(p => p.id === id))).length;
  return { covered: ids.size, points: crafting.filter(p => ids.has(p.id)).length * 3, craftCharacters, ids };
}
export function normalizeProgress(value) {
  const safe = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  return Object.fromEntries(crafting.map(p => [p.id, Number.isInteger(safe[p.id]) && safe[p.id] >= 0 && safe[p.id] <= 3 ? safe[p.id] : 0]));
}
export function countPoints(value) {
  return Object.values(normalizeProgress(value)).reduce((sum, rank) => sum + rank, 0);
}
