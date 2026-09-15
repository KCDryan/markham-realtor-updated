import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const templatePath = path.join(root, 'index.template.html');
const dataPath = path.join(root, 'realtors.json');
const outputPath = process.env.RENDER_OUTPUT ? path.resolve(process.env.RENDER_OUTPUT) : path.join(root, 'index.html');

const [template, rawData] = await Promise.all([
  readFile(templatePath, 'utf8'),
  readFile(dataPath, 'utf8'),
]);

const payload = JSON.parse(rawData);
const realtors = Array.isArray(payload.realtors) ? [...payload.realtors] : [];
realtors.sort((a, b) => Number(a.rank || 999) - Number(b.rank || 999));

const esc = (value = '') => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const attr = (value = '') => esc(value).replaceAll('\n', ' ');
const safeUrl = (value = '') => {
  try {
    const url = new URL(String(value));
    if (url.protocol === 'https:' || url.protocol === 'http:') return url.href;
  } catch {}
  return '#';
};

const formatNumber = (value) => new Intl.NumberFormat('en-CA').format(Number(value || 0));
const shortNumber = (value) => new Intl.NumberFormat('en-CA', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value || 0));
const avgRating = realtors.length
  ? realtors.reduce((sum, item) => sum + Number(item.rating || 0), 0) / realtors.length
  : 0;
const totalReviews = realtors.reduce((sum, item) => sum + Number(item.review_count || 0), 0);

const updatedIso = String(payload.updated_at || new Date().toISOString().slice(0, 10));
const updatedDate = new Date(`${updatedIso}T12:00:00Z`);
const updatedHuman = new Intl.DateTimeFormat('en-CA', {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
}).format(updatedDate);

const stars = (rating) => {
  const filled = Math.max(0, Math.min(5, Math.round(Number(rating || 0))));
  return Array.from({ length: 5 }, (_, index) => `
    <svg class="h-4 w-4 ${index < filled ? 'text-amber-400' : 'text-slate-200'}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 0 0 .95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 0 0-.364 1.118l1.07 3.292c.3.922-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 0 0-1.176 0l-2.8 2.034c-.784.57-1.838-.196-1.539-1.118l1.07-3.292a1 1 0 0 0-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81H7.03a1 1 0 0 0 .95-.69l1.07-3.292Z"/>
    </svg>`).join('');
};

const initials = (name) => {
  const parts = String(name || 'MR').replace(/[^A-Za-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean);
  return (parts.slice(0, 2).map(part => part[0]).join('') || 'MR').toUpperCase();
};

const rankAccent = (rank) => {
  if (rank === 1) return {
    card: 'border-amber-200 bg-gradient-to-br from-amber-50 via-white to-white',
    rank: 'bg-gradient-to-br from-amber-300 to-yellow-400 text-amber-950 shadow-amber-200/70',
    label: 'Top ranked',
    labelClass: 'bg-amber-100 text-amber-800',
    avatar: 'from-amber-100 to-orange-100 text-amber-900',
  };
  if (rank === 2) return {
    card: 'border-slate-200 bg-gradient-to-br from-slate-50 via-white to-white',
    rank: 'bg-gradient-to-br from-slate-200 to-slate-300 text-slate-800 shadow-slate-200/70',
    label: 'Featured',
    labelClass: 'bg-slate-100 text-slate-700',
    avatar: 'from-slate-100 to-slate-200 text-slate-800',
  };
  if (rank === 3) return {
    card: 'border-orange-200 bg-gradient-to-br from-orange-50 via-white to-white',
    rank: 'bg-gradient-to-br from-orange-300 to-amber-500 text-orange-950 shadow-orange-200/70',
    label: 'Featured',
    labelClass: 'bg-orange-100 text-orange-800',
    avatar: 'from-orange-100 to-amber-100 text-orange-900',
  };
  return {
    card: 'border-slate-200 bg-white',
    rank: 'bg-slate-950 text-white shadow-slate-200/50',
    label: 'Ranked profile',
    labelClass: 'bg-slate-100 text-slate-600',
    avatar: 'from-cyan-50 to-emerald-50 text-slate-800',
  };
};

const contactLabel = (url) => {
  try {
    return new URL(url).hostname.includes('google.com') ? 'View profile' : 'Visit website';
  } catch {
    return 'View profile';
  }
};

const cardHtml = (item) => {
  const rank = Number(item.rank || 0);
  const accent = rankAccent(rank);
  const specialties = Array.isArray(item.specialties) ? item.specialties : [];
  const contact = safeUrl(item.contact_link);
  const phone = String(item.phone || '').trim();
  const telHref = phone ? `tel:${phone.replace(/[^+\d]/g, '')}` : '';
  const searchBlob = [item.name, item.brokerage, item.address, item.locality, ...specialties].filter(Boolean).join(' ');
  const specialtyBlob = specialties.map(value => String(value).toLowerCase()).join('|');

  return `
    <article
      class="realtor-card relative overflow-hidden rounded-[1.75rem] border p-5 shadow-[0_18px_55px_-38px_rgba(15,23,42,.45)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_25px_65px_-35px_rgba(15,23,42,.45)] sm:p-6 ${accent.card}"
      data-realtor-card
      data-rank="${rank}"
      data-rating="${Number(item.rating || 0)}"
      data-reviews="${Number(item.review_count || 0)}"
      data-score="${Number(item.score || 0)}"
      data-search="${attr(searchBlob)}"
      data-specialties="${attr(specialtyBlob)}"
    >
      <div class="relative z-10">
        <div class="flex items-start gap-4">
          <div class="relative shrink-0">
            <div class="grid h-15 w-15 place-items-center rounded-2xl bg-gradient-to-br ${accent.avatar} text-lg font-black shadow-inner">${esc(initials(item.name))}</div>
            <div class="absolute -bottom-2 -right-2 grid h-8 min-w-8 place-items-center rounded-xl px-2 text-xs font-black shadow-lg ${accent.rank}">#${rank}</div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[.12em] ${accent.labelClass}">${accent.label}</span>
              ${item.locality ? `<span class="rounded-full border border-slate-200 bg-white/75 px-2.5 py-1 text-[10px] font-bold text-slate-500">${esc(item.locality)}</span>` : ''}
            </div>
            <h3 class="mt-2 text-xl font-black leading-tight tracking-[-.025em] text-slate-950">${esc(item.name)}</h3>
            <p class="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-slate-500">${esc(item.brokerage || 'Brokerage not listed')}</p>
          </div>
        </div>

        <div class="mt-5 grid grid-cols-3 gap-2 rounded-2xl border border-slate-200/70 bg-white/75 p-3 backdrop-blur">
          <div class="min-w-0 border-r border-slate-200 pr-2">
            <div class="text-[9px] font-black uppercase tracking-[.14em] text-slate-400">Rating</div>
            <div class="mt-1 flex items-center gap-1.5"><span class="text-lg font-black text-slate-950">${Number(item.rating || 0).toFixed(1)}</span><span class="text-sm text-amber-400">★</span></div>
          </div>
          <div class="min-w-0 border-r border-slate-200 px-2">
            <div class="text-[9px] font-black uppercase tracking-[.14em] text-slate-400">Reviews</div>
            <div class="mt-1 truncate text-lg font-black text-slate-950">${formatNumber(item.review_count)}</div>
          </div>
          <div class="min-w-0 pl-2">
            <div class="text-[9px] font-black uppercase tracking-[.14em] text-slate-400">Score</div>
            <div class="mt-1 text-lg font-black text-slate-950">${Number(item.score || 0).toFixed(1)}</div>
          </div>
        </div>

        <div class="mt-4 flex items-center gap-1" aria-label="${Number(item.rating || 0).toFixed(1)} out of 5 stars">${stars(item.rating)}<span class="ml-2 text-xs font-semibold text-slate-400">${esc(item.rating_source || 'Public business data')}</span></div>

        <div class="mt-4 flex flex-wrap gap-2">
          ${specialties.slice(0, 5).map(s => `<span class="rounded-full border border-cyan-100 bg-cyan-50 px-2.5 py-1 text-[11px] font-extrabold text-cyan-800">${esc(s)}</span>`).join('')}
        </div>

        <div class="mt-5 flex gap-3 border-t border-slate-200/80 pt-4 text-sm text-slate-500">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s7-4.4 7-11a7 7 0 1 0-14 0c0 6.6 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>
          <span class="line-clamp-2 leading-5">${esc(item.address || 'Markham, Ontario')}</span>
        </div>

        <div class="mt-5 flex flex-col gap-2 sm:flex-row">
          <a href="${attr(contact)}" target="_blank" rel="noopener noreferrer nofollow" class="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-black text-white shadow-lg shadow-slate-900/10 transition hover:bg-cyan-800">
            ${esc(contactLabel(contact))}
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5h5v5M10 14 19 5M19 13v6H5V5h6"/></svg>
          </a>
          ${phone ? `<a href="${attr(telHref)}" class="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-black text-slate-700 transition hover:border-cyan-200 hover:bg-cyan-50 hover:text-cyan-900"><svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.62 2.63a2 2 0 0 1-.45 2.11L8 9.73a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.85.29 1.73.5 2.63.62A2 2 0 0 1 22 16.92Z"/></svg>Call</a>` : ''}
        </div>
      </div>
    </article>`;
};

const topThreeHtml = realtors.slice(0, 3).map(item => {
  const rank = Number(item.rank || 0);
  const colors = rank === 1
    ? 'from-amber-300 to-yellow-400 text-amber-950'
    : rank === 2
      ? 'from-slate-200 to-slate-300 text-slate-800'
      : 'from-orange-300 to-amber-500 text-orange-950';
  return `
    <a href="#rankings" class="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[.065] p-4 transition hover:border-cyan-200/30 hover:bg-white/[.10]">
      <div class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br ${colors} text-sm font-black shadow-lg">#${rank}</div>
      <div class="min-w-0 flex-1">
        <div class="truncate text-sm font-black text-white sm:text-base">${esc(item.name)}</div>
        <div class="mt-0.5 truncate text-xs font-medium text-slate-400">${esc(item.brokerage || '')}</div>
      </div>
      <div class="shrink-0 text-right">
        <div class="text-sm font-black text-white">${Number(item.rating || 0).toFixed(1)} <span class="text-amber-300">★</span></div>
        <div class="mt-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-500">${formatNumber(item.review_count)} reviews</div>
      </div>
    </a>`;
}).join('');

const specialties = new Map();
for (const item of realtors) {
  for (const specialty of (Array.isArray(item.specialties) ? item.specialties : [])) {
    const label = String(specialty).trim();
    if (!label) continue;
    specialties.set(label, (specialties.get(label) || 0) + 1);
  }
}

const allSpecialties = [...specialties.keys()].sort((a, b) => a.localeCompare(b, 'en-CA'));
const specialtyOptions = allSpecialties.map(value => `<option value="${attr(value)}">${esc(value)}</option>`).join('\n');
const quickSpecialties = [...specialties.entries()]
  .filter(([label]) => !['markham', 'residential'].includes(label.toLowerCase()))
  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'en-CA'))
  .slice(0, 6)
  .map(([label]) => label);
const quickFilters = quickSpecialties.map(label => `<button type="button" data-specialty-chip="${attr(label)}" aria-pressed="false" class="specialty-chip">${esc(label)}</button>`).join('\n');

const itemListSchema = {
  '@context': 'https://schema.org',
  '@type': 'ItemList',
  name: 'Best Real Estate Agents in Markham, Ontario',
  description: 'A weekly updated independent directory of top real estate agents in Markham, Ontario.',
  itemListOrder: 'https://schema.org/ItemListOrderAscending',
  numberOfItems: realtors.length,
  itemListElement: realtors.map(item => ({
    '@type': 'ListItem',
    position: Number(item.rank || 0),
    item: {
      '@type': ['RealEstateAgent', 'LocalBusiness'],
      name: String(item.name || ''),
      url: safeUrl(item.contact_link),
      telephone: String(item.phone || '') || undefined,
      address: {
        '@type': 'PostalAddress',
        streetAddress: String(item.address || ''),
        addressLocality: String(item.locality || 'Markham'),
        addressRegion: 'ON',
        addressCountry: 'CA',
      },
      areaServed: {
        '@type': 'City',
        name: 'Markham',
      },
      memberOf: item.brokerage ? {
        '@type': 'Organization',
        name: String(item.brokerage),
      } : undefined,
    },
  })),
};

const safeJson = (value) => JSON.stringify(value, null, 2)
  .replaceAll('<', '\\u003c')
  .replaceAll('>', '\\u003e')
  .replaceAll('&', '\\u0026');

const replacements = {
  '{{ITEM_LIST_SCHEMA}}': safeJson(itemListSchema),
  '{{UPDATED_AT_HUMAN}}': esc(updatedHuman),
  '{{UPDATED_AT_ISO}}': esc(updatedIso),
  '{{AGENT_COUNT}}': String(realtors.length),
  '{{AVG_RATING}}': avgRating.toFixed(2),
  '{{TOTAL_REVIEWS_SHORT}}': esc(shortNumber(totalReviews)),
  '{{TOP_THREE}}': topThreeHtml,
  '{{SPECIALTY_OPTIONS}}': specialtyOptions,
  '{{QUICK_FILTERS}}': quickFilters,
  '{{REALTOR_CARDS}}': realtors.map(cardHtml).join('\n'),
  '{{METHODOLOGY_SUMMARY}}': esc(payload.methodology?.summary || 'Rankings use review quality, review volume, local-search visibility and profile completeness.'),
};

let output = template;
for (const [needle, replacement] of Object.entries(replacements)) {
  output = output.split(needle).join(replacement);
}

const unresolved = output.match(/\{\{[A-Z0-9_]+\}\}/g);
if (unresolved) {
  throw new Error(`Unresolved template placeholders: ${[...new Set(unresolved)].join(', ')}`);
}

await writeFile(outputPath, output, 'utf8');

if (!process.env.RENDER_OUTPUT) {
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://markhamrealtor.com/</loc>
    <lastmod>${updatedIso}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
`;
  await writeFile(path.join(root, 'sitemap.xml'), sitemap, 'utf8');
}

console.log(`Rendered ${path.relative(root, outputPath)} with ${realtors.length} realtor profiles.`);
