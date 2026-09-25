# Empire Vault Map

`intelligence vault build` exports transcript pages that slot into a Legends
Empire vault as cited evidence. This page maps the export layout to the Empire
side.

## Export layout

Under the batch intelligence directory:

```text
vault/
  index.md            # type: transcript-vault-index, wikilink list of pages
  <video_id>.md       # one page per transcribed video
```

Each transcript page carries frontmatter plus body:

```text
---
type: transcript
video_id: "<id>"
source_url: "<url>"
media_path: "<local path>"
word_count: <n>
---

# <video_id>

## Source

- Video ID, local media path, source URL

## Transcript

<full running text>
```

Pages use `[[wikilink]]` index entries, so the folder opens directly in Obsidian.

## Empire mapping

| Export artifact | Empire home | Notes |
|---|---|---|
| `vault/<video_id>.md` | Vault evidence area for the consuming project | Keep `video_id`, `source_url`, and `word_count` frontmatter intact |
| `vault/index.md` | Same folder as the pages | Rebuild the batch list if pages move |
| Batch `manifest.json` | Receipt or evidence note attachment | Provenance for rights basis and pull date |
| `words/<video_id>.words.jsonl` | Stays with the batch | Timing evidence; not vault reading material |
| Media files | Stay out of the vault | Vault holds citations, never binaries |

## Rules

- Cite pages by `video_id`, never by local media path. Paths are machine-local.
- Transcripts are evidence, not canon. Corrections live in new revisions with a
  note, not silent edits.
- Rights basis travels with the evidence: keep the batch manifest reference on
  any Empire note that quotes a transcript.
