import { buyFromDepth } from '../market/quotes.mjs';

export function quoteRecipe(recipe, quantity, inventory, fee, depth) {
  const batches = recipe.product && recipe.units ? Math.ceil(quantity / recipe.units) : quantity;
  const required = new Map();
  for (const item of recipe.materials || []) {
    const previous = required.get(item.id);
    required.set(item.id, { ...item, quantity: (previous?.quantity || 0) + item.quantity * batches });
  }
  const materials = [...required.values()].map(item => {
    const owned = Math.min(inventory.get(item.id) || 0, item.quantity);
    return { ...item, owned, ...buyFromDepth(depth, item.id, item.quantity - owned) };
  });
  const materialCost = materials.reduce((cost, item) => cost + item.spent, 0);
  const incomplete = !Array.isArray(recipe.materials) || (recipe.product && !recipe.units)
    || materials.some(item => item.missing);
  const direct = recipe.product ? buyFromDepth(depth, recipe.product.id, quantity) : null;
  const askingPrice = recipe.product ? depth?.depth[recipe.product.id]?.[0]?.[0] : null;
  const gross = !incomplete && recipe.units && askingPrice
    ? (recipe.units * batches * askingPrice - materialCost) / (recipe.units * batches) : null;
  const net = gross === null || fee === null ? null : gross - askingPrice * fee / 100;
  return { batches, materials, materialCost, incomplete, direct, askingPrice, gross, net };
}
