# Channel-Wide Link Sweeps and CTA Migrations

When a creator or company updates a primary call-to-action URL, retires a legacy domain, or reorganizes documentation, hundreds of older YouTube video descriptions can be left pointing to dead or outdated URLs.

## 1. Auditing Channel Description Links (`links-audit`)

First, export the channel's upload inventory (`2` quota units per 50 videos via the `UU...` uploads playlist), then run `links-audit`:

```bash
legends-youtube channel-inventory --mine --output inventory.json

legends-youtube links-audit \
  --inventory inventory.json \
  --canonical-cta "https://cto-legends.com" \
  --legacy-domains "old-example.com" \
  --json
```

- Pass `--probe-https` to send SSRF-guarded, no-redirect `HEAD` probes to unique public `https://` URLs and flag `404`, `5xx`, or `301`/`302` redirect chains.
- `links-audit` separates regular long-form videos (`format="long"`) from Shorts (`format="short"`) when checking `--canonical-cta`.

## 2. Generating a Hash-Locked Link Migration Plan (`links-migrate`)

`links-migrate` generates a `metadata-plan`-compatible JSON file with `expectedCurrent.description` locks on every matched video while excluding Shorts and any protected `--exclude-video-ids`:

```bash
legends-youtube links-migrate \
  --inventory inventory.json \
  --find-url "https://old-example.com/offer" \
  --replace-url "https://cto-legends.com" \
  --exclude-video-ids "VidLong0001,VidLong0002" \
  --output migration-plan.json
```

Review the generated `migration-plan.json` and `plan_sha256`, check quota capacity with `legends-youtube quota-plan`, and apply with `legends-youtube metadata-apply`.
