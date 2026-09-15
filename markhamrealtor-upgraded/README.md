# MarkhamRealtor.com

A premium, SEO-first local directory for comparing real estate agents in Markham, Ontario.

**Production domain:** https://markhamrealtor.com

**Cloudflare setup / 522 troubleshooting:** see `CLOUDFLARE-SETUP.md`.

The site is intentionally lightweight: Cloudflare Pages serves a static build, GitHub stores the source and GitHub Actions refreshes the ranking data every Sunday.

## What is upgraded in v2

- Premium dark hero and modern editorial layout
- Pre-rendered realtor cards for SEO
- Search, specialty filtering and sorting without a framework
- Top-three spotlight section
- Responsive ranking cards with rating, review count, score, specialties and contact actions
- Interactive OpenStreetMap embed for Markham
- Transparent methodology visualization
- FAQ accordion and FAQ structured data
- ItemList + RealEstateAgent/LocalBusiness JSON-LD
- OpenGraph social image and favicon
- Cloudflare security/cache headers
- Custom 404 page
- Weekly GitHub Actions data refresh
- Production safety stops if live data is missing or malformed

## Important architecture change

`realtors.json` remains the single source of truth, but the production build now **pre-renders the rankings into HTML**.

That means search engines and LLM crawlers can see agent names, brokerage details, specialties and ranking content directly in the HTML without needing to execute JavaScript.

The build flow is:

```text
realtors.json
     ↓
scripts/render.mjs
     ↓
index.html
     ↓
Tailwind CSS build
     ↓
dist/
     ↓
Cloudflare Pages
```

JavaScript is then used only for the interactive filtering, searching, sorting and mobile navigation.

## Project structure

```text
markhamrealtor/
├── .github/
│   └── workflows/
│       └── weekly_update.yml
├── assets/
│   ├── favicon.svg
│   └── og-image.svg
├── scripts/
│   └── render.mjs
├── src/
│   └── input.css
├── 404.html
├── _headers
├── index.html
├── index.template.html
├── manifest.webmanifest
├── package.json
├── realtors.json
├── requirements.txt
├── robots.txt
├── sitemap.xml
├── update_realtors.py
└── README.md
```

## Which file should I edit?

For layout/design changes, edit:

```text
index.template.html
```

For Tailwind/custom CSS, edit:

```text
src/input.css
```

For realtor ranking data, edit or regenerate:

```text
realtors.json
```

Do **not** manually maintain `index.html`. It is generated from `index.template.html` + `realtors.json` by:

```bash
npm run render
```

## Local setup

Requirements:

- Node.js 20+
- Python 3.12+
- npm

Clone the repository:

```bash
git clone https://github.com/YOUR-GITHUB-USERNAME/markhamrealtor.git
cd markhamrealtor
```

Install frontend dependencies:

```bash
npm install
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Build the production site:

```bash
npm run build
```

This creates:

```text
dist/
```

Preview the production build:

```bash
npm run preview
```

Then visit:

```text
http://localhost:8000
```

## Render HTML without compiling Tailwind

If you only want to regenerate `index.html` from the current JSON data:

```bash
npm run render
```

This does not require any external JavaScript framework.

## Update realtor data locally

Without a live API key, the Python script uses the deterministic development seed dataset:

```bash
python update_realtors.py
```

For live data:

```bash
export SERPER_API_KEY="YOUR_API_KEY"
python update_realtors.py
```

Windows PowerShell:

```powershell
$env:SERPER_API_KEY="YOUR_API_KEY"
python update_realtors.py
```

After the JSON changes, rebuild:

```bash
npm run build
```

## Realtor JSON format

The frontend/build expects this general structure:

```json
{
  "updated_at": "2026-09-15",
  "market": {
    "city": "Markham",
    "region": "Ontario",
    "country": "Canada"
  },
  "realtors": [
    {
      "rank": 1,
      "name": "Example Realtor",
      "brokerage": "Example Realty Brokerage",
      "rating": 4.9,
      "review_count": 250,
      "specialties": ["Markham", "Sellers", "Buyers"],
      "address": "Markham, ON",
      "locality": "Markham",
      "contact_link": "https://example.com",
      "phone": "+1 905-555-5555",
      "score": 95.2,
      "rating_source": "Public business data via search-data provider"
    }
  ]
}
```

## Ranking methodology

The current score is designed around four signals:

| Signal | Weight |
|---|---:|
| Bayesian-adjusted review quality | 60% |
| Review volume | 25% |
| Observed local-search visibility | 10% |
| Profile completeness | 5% |

The Bayesian adjustment reduces volatility from profiles with very few reviews.

No paid-placement factor is included in the current ranking formula.

## Markham location filtering

The live updater is designed to prioritize public business addresses in Markham-area postal prefixes:

```text
L3P
L3R
L3S
L3T
L6B
L6C
L6E
L6G
```

The eligibility filter also attempts to distinguish identifiable agents, brokers and teams from generic brokerage offices.

## GitHub secret

The weekly live update requires this repository secret:

```text
SERPER_API_KEY
```

Add it in GitHub:

```text
Repository
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Or with GitHub CLI:

```bash
gh secret set SERPER_API_KEY
```

## Weekly automation

The workflow is located at:

```text
.github/workflows/weekly_update.yml
```

It runs every Sunday at 00:00 UTC:

```yaml
cron: "0 0 * * 0"
```

The workflow:

1. Checks out the repository
2. Sets up Python
3. Installs Python dependencies
4. Validates the updater script
5. Fetches and scores fresh realtor data
6. Refuses to publish if live data is missing or insufficient
7. Validates the generated HTML using the refreshed JSON
8. Checks whether `realtors.json` materially changed
9. Commits and pushes only when needed
10. Cloudflare Pages detects the push and rebuilds the site

## Manually run the GitHub Action

Using GitHub CLI:

```bash
gh workflow run weekly_update.yml
```

Watch the run:

```bash
gh run watch
```

## Cloudflare Pages setup

In Cloudflare:

```text
Workers & Pages
→ Create application
→ Pages
→ Connect to Git
```

Select the GitHub repository and use:

```text
Production branch: main
Framework preset: None
Build command: npm run build
Build output directory: dist
Root directory: leave blank
```

The build script automatically:

1. Generates `index.html` from the latest `realtors.json`
2. Compiles/minifies Tailwind CSS
3. Copies the site assets into `dist/`

## Custom domain

After the first successful deployment:

```text
Cloudflare
→ Workers & Pages
→ your project
→ Custom domains
→ Set up a domain
```

Add:

```text
markhamrealtor.com
```

## SEO implementation

The production page includes:

- Semantic HTML5
- Fully pre-rendered realtor content
- Canonical URL
- Optimized title and meta description
- OpenGraph tags
- Twitter card metadata
- XML sitemap
- robots.txt
- WebSite schema
- Organization schema
- ItemList schema
- RealEstateAgent + LocalBusiness entities
- FAQPage schema
- Crawlable local-area content
- Human-readable ranking methodology

Third-party star ratings are displayed on the page but are intentionally **not** inserted into `AggregateRating` structured data.

## Cloudflare headers

`_headers` includes sensible defaults for:

- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `X-Frame-Options`
- cache rules for static assets
- shorter cache lifetime for `realtors.json`

## Data safety

The Python updater is intentionally defensive.

A production refresh can stop instead of overwriting the live data when:

- `SERPER_API_KEY` is missing
- the live provider request fails
- too few eligible Markham profiles are returned
- JSON generation fails
- the output is empty

This protects the existing directory from being replaced by an empty or obviously broken update.

## Data-source compliance

Before adding a new data source, review its:

- Terms of service
- API licence
- automated-access rules
- storage limits
- republication rights
- commercial-use restrictions

Prefer licensed APIs and first-party business websites over scraping sites that prohibit automated access or republication.

## Useful commands

Install dependencies:

```bash
npm install
python -m pip install -r requirements.txt
```

Refresh development data:

```bash
python update_realtors.py
```

Regenerate HTML:

```bash
npm run render
```

Build production files:

```bash
npm run build
```

Preview production:

```bash
npm run preview
```

Git commit:

```bash
git add .
git commit -m "Upgrade MarkhamRealtor.com design"
git push
```

## Legal / editorial disclosure

MarkhamRealtor.com is an independent directory.

Rankings are editorial and algorithmic estimates based on available data and are not official rankings from RECO, CREA, TRREB, any real estate board, brokerage or government body.

Inclusion does not imply endorsement, partnership or affiliation.

If sponsored placements are introduced in the future, they should be clearly labelled and kept separate from the organic ranking methodology.

REALTOR® is a trademark controlled by The Canadian Real Estate Association and identifies real estate professionals who are members of CREA.
