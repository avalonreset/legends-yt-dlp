# Attachable Empire Knowledge Pack (`legends-youtube`)

`legends-youtube` ships a versioned knowledge pack at `knowledge/youtube/pack.json` conforming to schema `legends.knowledge-pack/v1`.

## Contents

1. **12 Operator Runbooks (`wiki/*.md` & `knowledge/youtube/vault/*.md`):**
   - [index.md](../wiki/index.md)
   - [overview.md](../wiki/overview.md)
   - [authentication-and-quotas.md](../wiki/authentication-and-quotas.md)
   - [metadata-and-partial-updates.md](../wiki/metadata-and-partial-updates.md)
   - [zero-quota-public-readback.md](../wiki/zero-quota-public-readback.md)
   - [perfect-video-formula-and-idea-radar.md](../wiki/perfect-video-formula-and-idea-radar.md)
   - [title-thumbnail-and-description-sops.md](../wiki/title-thumbnail-and-description-sops.md)
   - [shorts-related-video-funnel-and-guards.md](../wiki/shorts-related-video-funnel-and-guards.md)
   - [analytics-and-packaging-ab.md](../wiki/analytics-and-packaging-ab.md)
   - [chapters-captions-and-quizzes.md](../wiki/chapters-captions-and-quizzes.md)
   - [draft-uploads-and-thumbnails.md](../wiki/draft-uploads-and-thumbnails.md)
   - [link-sweeps-and-playlists.md](../wiki/link-sweeps-and-playlists.md)
   - [troubleshooting.md](../wiki/troubleshooting.md)
2. **Primary Google & YouTube Documentation Sources (`sources.md`).**
3. **4 Operation Receipt Templates (`templates/*.md`).**

## Verifying and Attaching to `legends-empire`

Verify the pack offline at any time:

```bash
legends-youtube knowledge-pack --json
```

Suggested Empire ontology shelf: `wiki/library/legends-youtube/youtube`. Installing `legends-youtube` never modifies a user vault automatically; attachment uses `legends-empire`'s preview-first, conflict-safe transaction engine.
