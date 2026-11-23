# Working on this repository

Add a skill only when the owner asks for it by name or describes its purpose. Keep skills from local installations and other repositories out of this collection unless the owner explicitly requests an import.

## Skill layout

- Put each skill in `skills/micr-<kebab-case-name>/SKILL.md`. Every skill name starts with `micr-` so the collection stays recognizable next to other installed skills. Use the directory name, prefix included, as the `name` in its YAML frontmatter. When importing or renaming a skill, add the prefix to both.
- Write a `description` that tells an agent when to select the skill. In the body, explain how to carry out the task and how to check the result.
- Keep supporting examples, scripts, and reference material beside the skill that uses them. Link to those files from `SKILL.md` using relative paths.
- When adding, renaming, or removing a skill, update its entry in the root README. Give each entry a link and one sentence explaining when to use it.

## Verification

For a changed skill, check the frontmatter, follow its local links, and try one representative request. If the skill changes files or calls an external service, use disposable inputs for the check.
