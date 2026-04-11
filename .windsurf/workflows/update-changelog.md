---
description: Update changelog with recent changes
---

# Update Changelog

This workflow helps update the CHANGELOG.md file with recent changes to the codebase.

## Steps

1. Check the last entry in CHANGELOG.md to see the version and date of the last update
2. Get the git log since that date: `git log --since="YYYY-MM-DD" --oneline --all`
3. Check git status for uncommitted changes: `git status`
4. Review modified files to identify uncommitted changes
5. Review both committed and uncommitted changes and categorize them into:
   - Added: New features
   - Changed: Changes to existing functionality
   - Fixed: Bug fixes
   - Removed: Removed features
6. Update CHANGELOG.md with a new version entry (increment version as appropriate)
7. Follow Keep a Changelog format: https://keepachangelog.com/en/1.0.0/

## Notes

- Use semantic versioning for version numbers (MAJOR.MINOR.PATCH)
- MAJOR: Incompatible API changes
- MINOR: Backwards-compatible functionality additions
- PATCH: Backwards-compatible bug fixes
