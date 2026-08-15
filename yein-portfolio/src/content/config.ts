import { defineCollection, z } from 'astro:content';

const projects = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    category: z.enum(['art', 'essay', 'other']),
    date: z.date(),
    cover: z.string().optional(),
    summary: z.string(),
    draft: z.boolean().default(false),
  }),
});

const news = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.date(),
    sourceName: z.string(),
    sourceUrl: z.string().url(),
    cover: z.string().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

const about = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),
    tagline: z.string(),
    school: z.string(),
    grade: z.string(),
    location: z.string(),
    interests: z.array(z.string()).default([]),
    photo: z.string().optional(),
    favoriteMusic: z.string().optional(),
    favoriteMovies: z.string().optional(),
    favoriteShows: z.string().optional(),
    favoriteBooks: z.string().optional(),
  }),
});

export const collections = { projects, news, about };
