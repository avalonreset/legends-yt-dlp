# Description Chapters, Captions, and Studio Video Quizzes

`legends-youtube` provides deterministic validators for three high-leverage retention and discovery features: description chapters, caption tracks, and YouTube Studio Video Quizzes (`ytve-posts-modal`).

## 1. Video Description Chapters (`chapters-lint`)

YouTube silently disables interactive chapters on the video scrub bar if any of four rules are violated:

1. **Zero-Second Start:** The very first chapter timestamp must be `00:00` (or `0:00`).
2. **Minimum Count:** At least **3** chapters must be present.
3. **Strictly Ascending Order:** Every timestamp must be greater than the previous timestamp.
4. **10-Second Minimum Step:** Every chapter (including the final chapter relative to total video length) must span at least **10 seconds**.

```bash
legends-youtube chapters-lint --description-file description.txt --duration-seconds 1840 --json
```

## 2. YouTube Studio Video Quizzes (`quiz-lint`)

Interactive video quizzes in YouTube Studio (`<ytve-posts-modal>`) keep viewers engaged during technical long-form videos, but the Studio editor enforces strict validator rules:

| Rule | Hard Limit | Studio Validator Behavior |
| :--- | :--- | :--- |
| **Max quizzes per video** | `10` (`maximumPostsCount: 10`) | 5 quizzes (1 every 5 to 6 minutes) is optimal for 25-to-35-minute videos |
| **Options per quiz** | `2` to `4` options | Single-line only (`isNewLineForbidden: true`) |
| **Option text length** | `<= 80` characters | `>= 81` chars triggers `QUIZ_OPTION_TEXT_TOO_LONG` and disables `Save` |
| **Balanced option target** | `60` to `75` characters | Keep all 4 options within ~1 to 15 chars of each other so decoys are not shorter than the right answer |
| **Question stem** | Single-line (`85..130` chars target) | Move shared framing into the question stem to save option characters |
| **Explanation text** | `<= 500` characters | `>= 501` chars triggers `QUIZ_EXPLANATION_TEXT_TOO_LONG` |
| **Timestamp format** | `MM:SS:FF` (8 characters) | `ytcp-media-timestamp-input` requires 8-character strings such as `05:25:00` |

### The `00:00:00`-First Population Rule

When populating quizzes in YouTube Studio, clicking `+ Add quiz` spawns the new quiz row at `00:00:00`. Always fill the question stem, options `A..D`, correct-answer toggle, and explanation **while the row is still at `00:00:00`**, and set the `MM:SS:FF` timestamp **last**. Setting the timestamp first causes Studio to chronologically re-sort the rows mid-entry.

```bash
legends-youtube quiz-lint --quizzes-file quizzes.json --duration-seconds 1800 --json
```
