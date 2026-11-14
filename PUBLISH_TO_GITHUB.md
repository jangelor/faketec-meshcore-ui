# Publish FakeTec UI v0.5.2 source preview

The source is experimental and is not a compiled UF2 image. Verify the board and source build on hardware before making a binary available.

The repository is `https://github.com/jangelor/faketec-meshcore-ui`.

The first public binary is already published separately as v0.4.1. Do not overwrite or rename it as v0.5.2.

To update the repository with this source package, extract `faketec-meshcore-ui-v051-github-ready.zip`, compare it with your existing checkout, commit the new/updated source and docs, then push to the repository. Avoid force-pushing or replacing another user's changes.

For source-preview release notes, see `GITHUB_RELEASE_NOTES.md`. Only attach a `v0.5.2.uf2` after compilation, checksum verification, and physical testing of the exact image you upload.

Note: This ZIP omits `.github/workflows/validate.yml` because the user's GitHub PAT lacks workflow scope. Do not add or modify workflow files when pushing.
