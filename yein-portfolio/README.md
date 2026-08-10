# Yein Cho — Portfolio Website

Yein's personal portfolio site, built to be used as a reference when applying to university. It's made up of three pages:

- **About** (`/`) — introduction page
- **Projects** (`/projects/`) — a board for school work (Art / Essay / Other)
- **News Clips** (`/news/`) — a board for news stories she's found interesting

Content is managed through [Decap CMS](https://decapcms.org) at `/admin/`, so photos and writing can be uploaded without touching any code.

## Tech stack

- [Astro](https://astro.build) — static site generation
- [Decap CMS](https://decapcms.org) — browser-based post/photo uploads (Git-backed CMS)
- [Netlify](https://netlify.com) — free hosting + automatic deploys + login (Identity)

## Local development

```bash
cd yein-portfolio
npm install
npm run dev
```

Open `http://localhost:4321` to view it.

```bash
npm run build    # generates static files into dist/
npm run preview  # preview the production build
```

## Content structure

| Page | Content path |
|---|---|
| About | `src/content/about/index.md` (single file) |
| Projects | `src/content/projects/*.md` |
| News Clips | `src/content/news/*.md` |

Each markdown file has a frontmatter block (between the `---` lines) for fields like title, date, and category, followed by the body written in markdown. Posts created through `/admin/` are generated in this same format automatically.

---

## Netlify deployment & CMS setup (one-time)

This project lives inside the `yein-portfolio/` folder of a single GitHub repository (`hosephcho/hoseph`). Configure Netlify to build and deploy only that folder.

### 1. Connect the site to Netlify

1. Create a free account at [netlify.com](https://netlify.com) (you can sign in with GitHub)
2. **Add new site → Import an existing project → GitHub**, then select the `hosephcho/hoseph` repository
3. Choose the branch to deploy (e.g. `main`, or the branch currently in use)
4. Build settings:
   - **Base directory**: `yein-portfolio`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist` (relative to the base directory)
5. Click Deploy → you'll get a `https://[site-name].netlify.app` URL.

### 2. Enable Netlify Identity + Git Gateway (so Yein can log in and post)

1. Netlify site dashboard → **Site configuration → Identity → Enable Identity**
2. Set **Registration** to `Invite only` (so no one else can sign up)
3. Under Identity settings, go to **Services → Git Gateway → Enable Git Gateway**
4. Under **Identity → Invite users**, send an invite to Yein's email address
5. Yein clicks the invite link in her email, sets a password, and can then log in

### 3. Check the branch in `/admin/config.yml`

Make sure `backend.branch` in `public/admin/config.yml` matches whatever branch Netlify is actually deploying. If it doesn't, update it and push again:

```yaml
backend:
  name: git-gateway
  branch: main   # change to the actual deploy branch
```

### 4. Publishing a post

Once deployed, go to `https://[site-name].netlify.app/admin/` → log in → choose **Projects** or **News Clips** from the sidebar → click **New Project** / **New News Clip** to write a post with photos. It saves straight to GitHub, and Netlify automatically rebuilds the site — changes usually show up within a minute or two.

---

## Custom domain (optional)

Even on Netlify's free plan, you can connect a custom domain under **Site configuration → Domain management** (the domain itself needs to be purchased separately; the default `netlify.app` address works fine without one).

## Color palette

This site uses the "Lavender Blush" palette (defined as CSS variables in `src/styles/global.css`).

| Color | HEX |
|---|---|
| Lavender | `#C9BBEA` |
| Blush Pink | `#F6D4E4` |
| Cream (background) | `#FFF8F2` |
| Ink (text) | `#4A3B5C` |
