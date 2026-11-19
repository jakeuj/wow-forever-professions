import { characterSlug, classNames } from '../../players/model.mjs';

const api = 'https://tw.api.blizzard.com';
const refresh = 15 * 60 * 1000;
const cache = new Map();
let token;

function name(value) {
  return typeof value === 'string' ? value : value?.zh_TW || value?.en_US || '';
}

async function accessToken(env) {
  if (!env.BLIZZARD_CLIENT_ID || !env.BLIZZARD_CLIENT_SECRET) {
    const published = await env.SNAPSHOTS.get('battle-net-token');
    if (!published) throw new Error('Missing Blizzard authorization');
    return published;
  }
  if (token?.expires > Date.now()) return token.value;
  const response = await fetch('https://oauth.battle.net/token', {
    method: 'POST',
    headers: {
      Authorization: `Basic ${btoa(`${env.BLIZZARD_CLIENT_ID}:${env.BLIZZARD_CLIENT_SECRET}`)}`,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'grant_type=client_credentials',
    signal: AbortSignal.timeout(6000),
  });
  if (!response.ok) throw new Error('OAuth unavailable');
  const data = await response.json();
  if (!data.access_token || !Number.isFinite(data.expires_in)) throw new Error('Invalid OAuth response');
  token = { value: data.access_token, expires: Date.now() + Math.max(0, data.expires_in - 60) * 1000 };
  return token.value;
}

async function lookup(env, path, namespace, authRetry = true) {
  const url = new URL(path, api);
  url.search = new URLSearchParams({ namespace: `${namespace}-forever-tw`, locale: 'zh_TW' });
  const access = await accessToken(env);
  const response = await fetch(url, { headers: { Authorization: `Bearer ${access}` }, signal: AbortSignal.timeout(7000) });
  if (response.status === 404) return null;
  if (response.status === 401 && authRetry) {
    if (token?.value === access) token = null;
    return lookup(env, path, namespace, false);
  }
  if (!response.ok) throw new Error('Upstream unavailable');
  return response.json();
}

function remember(key, value) {
  if (cache.size >= 256) cache.delete(cache.keys().next().value);
  cache.set(key, { value, expires: Date.now() + refresh });
}

function stats(data) {
  const attributes = {};
  for (const row of data.stats || []) {
    const stat = row.type?.type || name(row.type?.name);
    if (stat && Number.isFinite(row.value)) attributes[stat] = row.value;
  }
  const armor = data.armor?.value ?? data.armor;
  if (Number.isFinite(armor)) attributes['護甲'] = armor;
  const dps = data.weapon?.dps?.value ?? data.weapon?.dps;
  if (Number.isFinite(dps)) attributes['每秒傷害'] = dps;
  return attributes;
}

function equipped(data) {
  return (data?.equipped_items || []).filter(row => Number.isSafeInteger(row.item?.id)).map(row => ({
    id: row.item.id, name: name(row.name) || name(row.item?.name), slot: row.slot?.type, slotName: name(row.slot?.name),
    level: row.level?.value, stats: stats(row),
    enchants: (row.enchantments || []).map(enchant => name(enchant.display_string) || name(enchant.enchantment?.name)).filter(Boolean),
  }));
}

function skills(data) {
  return (data?.primaries || []).map(row => {
    const tiers = [...(row.tiers || [])].sort((a, b) => (b.skill_points || 0) - (a.skill_points || 0));
    const recipes = new Map(tiers.flatMap(tier => (tier.known_recipes || []).map(recipe => [recipe.id, name(recipe.name)])));
    return { id: row.profession?.id, name: name(row.profession?.name), skill: tiers[0]?.skill_points ?? 0,
      maxSkill: tiers[0]?.max_skill_points ?? 0, recipes: [...recipes] };
  });
}

function talents(data) {
  return (data?.specializations || []).map(row => ({
    name: name(row.specialization?.name) || name(row.name),
    loadouts: (row.loadouts || []).map(loadout => ({
      active: Boolean(loadout.is_active),
      talents: [...(loadout.selected_class_talents || []), ...(loadout.selected_spec_talents || []), ...(loadout.selected_talents || [])]
        .map(talent => ({ name: name(talent.tooltip?.spell_tooltip?.spell?.name) || name(talent.talent?.name) || name(talent.name),
          rank: talent.rank ?? talent.tooltip?.talent_rank ?? 1 })).filter(talent => talent.name),
    })),
    talents: (row.talents || []).map(talent => ({ name: name(talent.spell_tooltip?.spell?.name) ||
      name(talent.talent?.name) || name(talent.spell?.name) || name(talent.name),
    rank: talent.talent_rank ?? talent.rank ?? 1 })).filter(talent => talent.name),
    points: row.spent_points ?? row.points_spent,
  }));
}

export async function armoryResponse(request, env, path, headers) {
  if (request.method !== 'GET') return new Response(null, { status: 405, headers: { ...headers, Allow: 'GET' } });
  const character = path.kind === 'characters';
  const key = character ? characterSlug(path.value) : /^\d{1,9}$/u.test(path.value) ? path.value : null;
  if (!key) return new Response(null, { status: 400, headers });
  try {
    const rate = await env.PROFILE_RATE.limit({ key: request.headers.get('CF-Connecting-IP') || 'local' });
    if (!rate.success) return new Response(null, { status: 429, headers: { ...headers, 'Retry-After': '60' } });
    const blocked = character ? await env.SNAPSHOTS.get('character-exclusions', 'json') : null;
    if (character && !Array.isArray(blocked)) return new Response(null, { status: 503, headers });
    const cacheKey = `${path.kind}:${key}`;
    const cached = cache.get(cacheKey);
    if (cached?.expires > Date.now()) {
      const { id, data } = cached.value;
      return character && blocked.includes(id)
        ? new Response(null, { status: 404, headers })
        : Response.json(data, { headers });
    }
    if (!character) {
      const item = await lookup(env, `/data/wow/item/${key}`, 'static');
      if (!item) return new Response(null, { status: 404, headers });
      const preview = item.preview_item || {};
      const data = { id: item.id, name: name(item.name), slot: item.inventory_type?.type, slotName: name(item.inventory_type?.name),
        level: preview.level?.value ?? item.level, stats: stats(preview),
        binding: preview.binding?.type, requiredLevel: item.required_level,
        source: name(item.source?.name) || name(preview.source?.name) };
      remember(cacheKey, { id: item.id, data });
      return Response.json(data, { headers });
    }
    const resource = `/profile/wow/character/${encodeURIComponent(key)}`;
    const info = await lookup(env, resource, 'profile');
    if (!info || blocked.includes(info.id)) return new Response(null, { status: 404, headers });
    if (!Number.isSafeInteger(info.id)) throw new Error('Invalid character profile');
    const sections = ['equipment', 'professions', 'specializations'];
    const fields = await Promise.allSettled(sections.map(section => lookup(env, `${resource}/${section}`, 'profile')));
    const [gear, professions, specs] = fields.map(result => result.status === 'fulfilled' ? result.value : null);
    const data = { slug: key, name: [name(info.name), name(info.surname)].filter(Boolean).join(' ') || key,
      level: info.level, className: classNames[info.character_class?.id] || classNames[info.playable_class?.id]
        || name(info.character_class?.name) || name(info.playable_class?.name),
      guild: name(info.guild?.name), equipment: equipped(gear), professions: skills(professions), talents: talents(specs),
      fetchedAt: new Date().toISOString(), missing: sections.filter((_, index) => !fields[index].value) };
    const latestBlocked = await env.SNAPSHOTS.get('character-exclusions', 'json');
    if (!Array.isArray(latestBlocked)) return new Response(null, { status: 503, headers });
    if (latestBlocked.includes(info.id)) return new Response(null, { status: 404, headers });
    if (!data.missing.length) remember(cacheKey, { id: info.id, data });
    return Response.json(data, { headers });
  } catch {
    return new Response(null, { status: 503, headers });
  }
}
