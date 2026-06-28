# Jeremy Adventure Game — Agent Instructions

## Project

- The project root is the repository root (the directory containing this file).
- Read `SPEC.md` before changing gameplay. It is the intended source of truth.
- This is an open-ended, menu-driven adventure RPG with travel, gathering,
  crafting, equipment, positional combat, leveling, and scaling dungeons.
- Preserve the user's existing uncommitted work. Do not discard or overwrite
  unrelated changes.
- Run `pytest -q` after gameplay changes.

## Artwork

- Always put generated PNG files directly in this project directory.
- Final requested concept images should be 300x200 pixels unless the user says
  otherwise.
- Overworld movement and combat are separate screens:
  - Paths belong to the top-down overworld movement/exploration screen.
  - Battles use a dedicated battle scene and battle interface.
- The preferred look is a colorful early-2000s handheld pixel-art RPG, but all
  characters, creatures, maps, tiles, fonts, UI borders, icons, palettes, and
  other assets must be original.
- Do not copy Pokemon assets or create a close reproduction of Pokemon trade
  dress. Preserve only broad ideas such as top-down exploration, pixel art,
  and turn-based menu combat.
- `jeremy-original-overworld.png` is the copyright-safer published concept.
- The older Pokemon-like drafts are local experiments and must not be committed
  or published unless the user explicitly requests it:
  - `jeremy-emerald-style-overworld.png`
  - `jeremy-game-concept.png`
  - `jeremy-overworld-path.png`
  - `jeremy-pokemon-path-battle.png`

## Git and GitHub

- GitHub account: `cutepokemon42`.
- Private repository: `git@github.com:cutepokemon42/jeremy_adventure_game.git`.
- Keep the repository private unless the user explicitly requests otherwise.
- All commits must use:
  - Name: `Jeremy Chen`
  - Email: `297719799+cutepokemon42@users.noreply.github.com`
- The repository-local Git configuration is already set to that identity.
- Push this repository with the SSH key `~/.ssh/jeremy1`. Never print or copy
  the private key. Use:

  ```sh
  GIT_SSH_COMMAND='ssh -i ~/.ssh/jeremy1 -o IdentitiesOnly=yes' git push
  ```

- GitHub CLI has multiple accounts configured. Ensure `cutepokemon42` is active
  for repository API operations; switch with:

  ```sh
  gh auth switch --user cutepokemon42
  ```

- The published history was intentionally rewritten so every existing commit's
  author and committer are Jeremy Chen. Do not reintroduce another author or
  committer identity.

## Save, Commit, and Push Checklist

Before committing or pushing, a future agent must:

1. Work from the repository root and save all project files there. Save
   generated PNGs in the repository root as well.
2. Review `git status` and stage only files intended for publication. Keep the
   four older Pokemon-like image drafts untracked unless explicitly requested.
3. Confirm the repository-local commit identity:

   ```sh
   git config user.name 'Jeremy Chen'
   git config user.email '297719799+cutepokemon42@users.noreply.github.com'
   ```

4. Commit normally, then verify both author and committer before pushing:

   ```sh
   git show -s --format='author=%an <%ae>%ncommitter=%cn <%ce>' HEAD
   ```

5. Confirm GitHub CLI is using the correct account for API operations:

   ```sh
   gh auth switch --user cutepokemon42
   ```

6. Push to `origin` using only Jeremy's SSH identity:

   ```sh
   GIT_SSH_COMMAND='ssh -i ~/.ssh/jeremy1 -o IdentitiesOnly=yes' git push origin main
   ```

7. Verify the remote branch with the same SSH identity. A plain `git ls-remote`
   may select another configured GitHub account and fail against this private
   repository:

   ```sh
   GIT_SSH_COMMAND='ssh -i ~/.ssh/jeremy1 -o IdentitiesOnly=yes' \
     git ls-remote origin refs/heads/main
   ```
