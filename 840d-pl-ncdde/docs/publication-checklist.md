# GitHub publication checklist

The files supplied here are a **curated publication snapshot**. Review this checklist before pushing to a public repository.

- [ ] Confirm the operator/owner consents to publishing the selected names and values. The fixture includes machine-specific observations such as `CHAN1` and the nominal motor current `17.6`.
- [ ] Verify authorship and the proposed MIT license for all original project code and scripts. If any imported file came from a third party with a different license, obtain permission or remove it.
- [ ] Do not add the privately supplied `windows.zip`, full PCU image, real Siemens `.exe`/`.dll`/`.ocx`, original `.NSK` tables, controller backup, binary disassembly dumps or trace captures.
- [ ] Keep original equipment paths, SIDs, names, IP addresses, log filenames, user identifiers, software keys and serial numbers out of public issues and code.
- [ ] Keep `windows/bin/ncdde_md_probe.exe`, compiled binary files and `windows/logs/*.txt` out of Git (already ignored).
- [ ] Review `docs/safety.md`. Do not remove the cautions about earlier drive alarms or expand default tests into drive polling.
- [ ] Run `python3 tools/verify_frames.py` and `python3 -m unittest discover -s tests -v`.
- [ ] Run `git status --ignored` after `git init` to ensure private material was not added inadvertently.
- [ ] If the fixture values are not approved for publication, delete or replace the whole `fixtures/observed_frames.json` and adjust field-test documentation and tests before publishing. Do **not** substitute synthetic frames without labeling them as synthetic.
- [ ] Confirm all links work in GitHub preview and make the first release a **research snapshot**, not a production-ready client.

## Example Git commands

```bash
git init
git add .
git status
git commit -m "Initial NCDDE research documentation and XP diagnostic source"
# Add your own repository remote when created:
# git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPO.git
# git branch -M main
# git push -u origin main
```

The package does not automatically publish anything to GitHub.
