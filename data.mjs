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
export const paladinRoutes = {
  keep: {
    letter: 'A', label: '保留現況', pair: '採礦／鍛造', short: '主角不更換專業', recommended: true,
    title: '保留採礦／鍛造，讓小號集中其他製造。',
    description: '適合目前已學採礦／鍛造、想先延續投入的玩家。法師與獵人各學雙製造，聖騎士供礦給自己與盜賊，盜賊的第二格保留彈性。',
    change: '聖騎士保留採礦／鍛造；先建立法師裁縫／附魔，再逐步補齊其他工匠。',
    flow: '聖騎士的礦供自身鍛造與盜賊工程；德魯伊的草與皮供獵人；布料與可寄綠裝交法師。',
    fit: '優先保留目前投入、想少洗專業的玩家。之後盜賊能穩定供礦時，也能銜接 B 路線。',
    note: '五種職業、九項專業全部涵蓋，四位製造角色合計最多 18 點。盜賊只須工程即可補齊製造，第二格可留空或依玩法選擇。',
    rows: [
      { ...paladin, reason: '維持採礦／鍛造；採到的礦料也可供應盜賊工程。' },
      { ...mage, order: '第一隻小號' },
      { ...hunter, order: '雙製造小號', role: '製皮與煉金', profs: ['leatherworking', 'alchemy'], reason: '接收德魯伊的皮料與草藥，同時發展製皮／煉金。' },
      { ...druid, order: '雙採集小號', role: '草藥與皮料', profs: ['herbalism', 'skinning'], reason: '採草與剝皮集中供應獵人；採集角仍需能前往相應地圖。' },
      { ...rogue, order: '工程小號', role: '工程與彈性格', profs: ['engineering'], flexibleSlot: true, reason: '接收聖騎士的礦料發展工程，第二格保持彈性。' },
    ],
  },
  crafting: {
    letter: 'B', label: '主角雙製造', pair: '鍛造／工程學', short: '採礦移交盜賊',
    title: '鍛造留在聖騎士，再加入工程工具。',
    description: '聖騎士把採礦換成工程，盜賊接手供礦。主角、法師與獵人各學雙製造，六項製造集中在三位角色；主角自己也是工匠。',
    change: '聖騎士採礦 → 工程；盜賊改學採礦。先備妥替代礦料來源，再考慮更換。',
    flow: '盜賊的礦供聖騎士鍛造／工程；德魯伊的草與皮供獵人；布料與可寄綠裝交法師。',
    fit: '想保留鍛造自用效益並增加工程工具的玩家。工程是此路線的具體示例，第二項製造仍可依坦／補／懲戒或 PvP 需求重配。',
    note: '五種職業、九項專業、三位製造角色，最多 18 點。與 A 相比，主角的採礦與盜賊的工程互換；其餘三隻角色的專業不必改。',
    rows: [
      { ...paladin, role: '主角雙製造', profs: ['blacksmithing', 'engineering'], reason: '保留鍛造，把採礦換成工程；兩項製造都由主角使用。' },
      { ...mage, order: '雙製造小號' },
      { ...hunter, order: '雙製造小號', role: '製皮與煉金', profs: ['leatherworking', 'alchemy'], reason: '接收德魯伊的皮料與草藥，同時發展製皮／煉金。' },
      { ...druid, order: '雙採集小號', role: '草藥與皮料', profs: ['herbalism', 'skinning'], reason: '採草與剝皮集中供應獵人。' },
      { ...rogue, order: '採礦採集角', role: '礦料與彈性格', profs: ['mining'], flexibleSlot: true, reason: '礦料集中供應聖騎士的鍛造／工程，第二格可留空或另選。' },
    ],
  },
  gathering: {
    letter: 'C', label: '主角專心採集', pair: '採礦／剝皮', short: '鍛造移交戰士',
    title: '主角保留採礦，製造工作交給小號。',
    description: '此例聖騎士把鍛造換成剝皮，任務路上採礦與收皮；戰士承接鍛造／工程，法師與獵人各學雙製造，德魯伊提供草藥。',
    change: '聖騎士鍛造 → 剝皮；鍛造交給戰士。更換前先盤點目前鍛造等級、配方與仍想自用的製造裝備。',
    flow: '聖騎士的礦供戰士，皮料供獵人；德魯伊的草藥供獵人煉金；布料與可寄綠裝交法師。',
    fit: '平常主要玩聖騎士、希望主角收材料而讓小號生產的玩家。若偏好採礦／採草，可讓德魯伊改負責剝皮，再重新分工。',
    note: '五種職業、九項專業、三位製造小號，最多 18 點。這條路會更換主角的鍛造；部分製造裝備拾取綁定，收益會留在承接工作的工匠本人。',
    rows: [
      { ...paladin, role: '主角雙採集', profs: ['mining', 'skinning'], reason: '保留採礦，把鍛造換成剝皮；礦供戰士、皮供獵人。' },
      { ...mage, order: '雙製造小號' },
      { ...hunter, order: '雙製造小號', role: '製皮與煉金', profs: ['leatherworking', 'alchemy'], reason: '皮料由聖騎士提供，草藥由德魯伊提供，集中製皮／煉金。' },
      { ...warrior, order: '雙製造小號', role: '鍛造與工程', profs: ['blacksmithing', 'engineering'], reason: '承接鍛造與工程，接收聖騎士提供的礦料。' },
      { ...druid, order: '草藥採集角', role: '草藥與彈性格', profs: ['herbalism'], flexibleSlot: true, reason: '草藥供應獵人煉金；第二格可留空或依玩法選擇。' },
    ],
  },
};
export function getPaladinRoute(routeId = 'keep') {
  return Object.hasOwn(paladinRoutes, routeId) ? paladinRoutes[routeId] : paladinRoutes.keep;
}
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
    label: '聖騎士多路線', tag: 'PLAN D · 聖騎士路線比較', title: '從現有採礦／鍛造出發，考慮三條分工路線。',
    description: '可先保留現況、改成主角雙製造，或把製造移交小號。三條路線都提供完整的全帳號分工，切換比較需要更換的專業與供料方式。',
    note: paladinRoutes.keep.note,
    rows: paladinRoutes.keep.rows,
  },
};
export function getRows(planId, stage = 'final', routeId = 'keep') {
  const plan = plans[planId] || plans.crafting;
  if (planId === 'paladin') return getPaladinRoute(routeId).rows.map(row => ({ ...row, profs: [...row.profs] }));
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
