# Cloudflare Pages Setup for markhamrealtor.com

This project is designed to be deployed with **Cloudflare Pages** from GitHub.

## Correct production domain

- Primary: `https://markhamrealtor.com`
- Optional redirect: `https://www.markhamrealtor.com` → `https://markhamrealtor.com`

## If you see Cloudflare Error 522

A 522 means Cloudflare can reach its own edge, but it cannot reach the origin currently configured for the hostname.

For a Cloudflare Pages site, the most common cause is that the domain still points to an old A/AAAA origin or that a CNAME was created manually without first attaching the hostname to the Pages project.

### 1. Confirm the Pages deployment works

Open your Pages development hostname:

`https://YOUR-PROJECT.pages.dev`

If that works, the website build is healthy and the remaining problem is the custom-domain/DNS configuration.

### 2. Attach the domain from the Pages project

In Cloudflare:

1. Go to **Workers & Pages**.
2. Open your Pages project.
3. Open **Custom domains**.
4. Click **Set up a domain**.
5. Enter `markhamrealtor.com`.
6. Complete the setup and wait until the domain status is **Active**.

Do this from the Pages project itself. Do not rely on creating a DNS record manually first.

### 3. Remove old origin records

Go to **Cloudflare → markhamrealtor.com → DNS → Records**.

Look for old records at the root hostname (`@` / `markhamrealtor.com`), especially:

- `A` records pointing to an old web-hosting IP
- `AAAA` records pointing to an old IPv6 origin
- a `CNAME` pointing to an old host

If the site is now hosted entirely on Cloudflare Pages, remove conflicting old root records after confirming they are not required for another service.

Do **not** delete MX, TXT, DKIM, SPF or other email records just because they reference the same domain.

### 4. Let Cloudflare create the Pages DNS record

When the zone is already on Cloudflare and the custom domain is attached correctly, Cloudflare normally creates/manages the required Pages DNS mapping.

The effective destination should be your Pages hostname, such as:

`YOUR-PROJECT.pages.dev`

Cloudflare Pages does not require an origin-server A record.

### 5. Add www if desired

You can also attach:

`www.markhamrealtor.com`

Then configure a permanent 301 redirect from `www.markhamrealtor.com` to `https://markhamrealtor.com` so the apex domain remains canonical.

### 6. Verify

Check all three:

- `https://YOUR-PROJECT.pages.dev`
- `https://markhamrealtor.com`
- `https://www.markhamrealtor.com` if configured

The first two should load without a 522. If `pages.dev` works while the custom domain still returns 522, re-check the Pages **Custom domains** screen and the DNS records for conflicting A/AAAA/CNAME entries.

## Cloudflare Pages build settings

Use:

- Framework preset: `None`
- Production branch: `main`
- Build command: `npm run build`
- Build output directory: `dist`
- Root directory: leave blank

## GitHub secret

Add:

`SERPER_API_KEY`

under **GitHub → Repository → Settings → Secrets and variables → Actions**.
