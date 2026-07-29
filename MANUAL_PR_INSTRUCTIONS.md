# Manual PR Instructions

To publish the feature branch and open a pull request manually, run the following commands from your local machine with network access and appropriate GitHub permissions:

```bash
git checkout atlas/large-document-production-hardening
git status
git push -u origin atlas/large-document-production-hardening
```

After pushing, create a pull request via the GitHub web UI or using the `gh` CLI:

```bash
gh pr create --title "Production hardening of Atlas large-document ingestion pipeline" \
  --body-file release_pr_body.md \
  --base main \
  --head atlas/large-document-production-hardening
```

If your repository policy requires opening PRs from a fork, push the branch to your fork and then create the PR targeting `jsherbanee/atlas-core:main`.
