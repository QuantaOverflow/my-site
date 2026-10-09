import { Client } from '@notionhq/client';
import { NotionToMarkdown } from 'notion-to-md';
import { writeFileSync, existsSync, readdirSync, unlinkSync, mkdirSync } from 'fs';
import { join, dirname, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, '../src/pages/writing');
const IMAGE_DIR = join(__dirname, '../public/notion-images');

const notion = new Client({ auth: process.env.NOTION_TOKEN });
const n2m = new NotionToMarkdown({ notionClient: notion });

// Notion file URLs expire after about an hour, so uploaded images are
// copied into the repo and referenced by a site path instead
mkdirSync(IMAGE_DIR, { recursive: true });
n2m.setCustomTransformer('image', async (block) => {
  const image = block.image;
  const caption = image.caption?.map((t) => t.plain_text).join('') ?? '';
  if (image.type === 'external') return `![${caption}](${image.external.url})`;

  const url = image.file.url;
  const name = `${block.id}${extname(new URL(url).pathname) || '.png'}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Image download failed (${res.status}) for block ${block.id}`);
  writeFileSync(join(IMAGE_DIR, name), Buffer.from(await res.arrayBuffer()));
  return `![${caption}](/notion-images/${name})`;
});

// Fetch all published articles from Notion
const response = await notion.databases.query({
  database_id: process.env.NOTION_DATABASE_ID,
  filter: { property: 'Status', select: { equals: 'Published' } },
});

const publishedSlugs = new Set();

for (const page of response.results) {
  const props = page.properties;

  const title = props.Title?.title?.[0]?.plain_text ?? '';
  const slug = props.Slug?.rich_text?.[0]?.plain_text ?? '';
  const description = props.Description?.rich_text?.[0]?.plain_text ?? '';
  const date = props.Date?.date?.start ?? '';
  const tags = props.Tags?.multi_select?.map((t) => t.name) ?? [];

  if (!slug) {
    console.warn(`Skipping "${title}" — no slug set`);
    continue;
  }

  // Convert Notion page body to Markdown
  const mdBlocks = await n2m.pageToMarkdown(page.id);
  const content = n2m.toMarkdownString(mdBlocks).parent;

  const frontmatter = [
    '---',
    `layout: ../../layouts/Article.astro`,
    `title: "${title.replace(/"/g, '\\"')}"`,
    `date: ${date}`,
    `description: "${description.replace(/"/g, '\\"')}"`,
    `tags: [${tags.join(', ')}]`,
    '---',
    '',
  ].join('\n');

  const filePath = join(OUTPUT_DIR, `${slug}.md`);
  writeFileSync(filePath, frontmatter + content, 'utf-8');
  publishedSlugs.add(`${slug}.md`);
  console.log(`✓ ${slug}.md`);
}

// Remove .md files that are no longer published
// (skip placeholder articles that don't come from Notion)
const existing = readdirSync(OUTPUT_DIR).filter((f) => f.endsWith('.md'));
for (const file of existing) {
  if (!publishedSlugs.has(file)) {
    console.log(`- Skipping local file: ${file} (not from Notion)`);
  }
}

console.log(`\nSync complete. ${publishedSlugs.size} article(s) written.`);
