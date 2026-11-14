---
lab5_triage:
  image: ghcr.io/fredo-js/itsm@sha256:cf27a0046d207ffcf6a5a265ac059bf672173dab3ef2cc3f3d2c001b58880700
  sarif_receipt: 417
---
<!-- ai-generated: 70% - Claude Code drafted the rows and the bake-off reading from the SARIF and the matrix; the decisions are my review of them -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which. The two scanner
findings on my own code come first; the rows after them cover the canary set, whose findings are seeded by the course
and live only on the never-merged branch `lab5/canary`. `.trivyignore` and `.gitleaksignore` are empty: the `image`
gate went green on `main` without any ignore, after the Dockerfile was hardened (base pinned by digest, `apt-get
upgrade`, pip removed after the install).

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| semgrep | dockerfile.security.missing-user.missing-user | accept | Dockerfile line 24 (the CMD) has no USER before it, so svcdesk runs as root inside its container. The container has no host mounts and no secrets, and the service only listens on 8080; I accept it for Lab 5 and will add a non-root USER and a chown of /data in a later lab, once the named volume's ownership is tested against every checker. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | src/svcdesk/kb.py line 26 opens a URL built from KB_INDEX_URL, which is deployment configuration set in docker-compose.yml, not request input; the scheme and host are fixed there and the only dynamic part, the search query, is percent-encoded with safe='' before it is appended. |
| trivy | CVE-2021-32677 | accept | Seeded pin in lab5-canary/requirements.txt (fastapi), found only on the canary branch, which is never merged; main's requirements.txt is clean, so the deps gate is green there and red on the canary, as P-08 asks. Kept until the grade arrives. |
| gitleaks | github-pat | accept | Seeded fake GitHub token in lab5-canary/config/github.py; it exists only on the canary branch, which must stay unedited until the grade arrives (P-07), and no real credential is involved. |
| semgrep | python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2 | false-positive | lab5-canary/app/email_render.py line 4: my bake-off counts it as the one Semgrep false positive, because the label key marks no defect there; the code is never run and the branch is never merged, so nothing is exposed. |

## Bake-off

On my canary set of 10 defects, trivy and semgrep were the best detectors with recall 0.4, and trivy had the better
F1 (0.5714 against 0.5333). Trivy found 4 defects with no false positive (precision 1.0): both vulnerable pins and two
of the three credentials. Semgrep found 4 as well, but a different four: three code defects (A02, A11, A14) and one
credential, at the price of one false positive (precision 0.8), the Jinja2 call in email_render.py. Gitleaks found
3 credentials (recall 0.3, precision 1.0), while grype and osv-scanner each found only the two pins (recall 0.2,
F1 0.3333), with no false positives at all. I would put trivy and gitleaks in the blocking gate, since both were
perfectly precise and a gate that never cries wolf is one people keep, and run semgrep as a reporting scanner whose
findings are read by a person, which is what the skeleton does. The surprise is that trivy and gitleaks overlap on the
credentials, so a second secrets tool adds little here. No detector found A03 (a path traversal in
attachment_read.py) and A08 (a predictable token generator in reset_tokens.py): both are about how a value flows or
how random it is, which pattern rules without taint tracking do not see. Every recall above is an upper bound, because
seeded defects flatter every detector (real defects are found several times less often), and my set is only ten
defects, so one more or one fewer finding moves a score by ten points.
