# Enable Codespaces prebuilds

This repository is already structured so Codespaces can prebuild the dev environment.

## GitHub UI steps

1. Open your repository on GitHub.
2. Go to **Settings** -> **Codespaces** -> **Prebuilds**.
3. Click **Set up prebuild**.
4. Choose:
   - Branch: `main`
   - Dev container configuration: `.devcontainer/devcontainer.json`
   - Trigger: **On configuration change** for low-cost MVP work, or **Every push** if you want faster refreshes.
5. Save.

## Recommended settings for this MVP

- Start with one prebuild on `main`.
- Use **On configuration change** until your environment stabilizes.
- Switch to **Every push** only if codespace spin-up is still too slow.

## What will be prebuilt

Because the heavy setup is in `.devcontainer/on-create.sh` and is called via `updateContentCommand`, GitHub can pre-run the package install and initial CMake configure during prebuild creation.
