# Security Policy

## Supported versions

Security fixes are applied to the latest release and the `main` branch. Older
prompt bundles, generated model artifacts, and deployment snapshots are not
maintained independently.

## Report a vulnerability privately

Use GitHub's private vulnerability reporting flow:

<https://github.com/hwl668/Scientific-learning-skills-/security/advisories/new>

If that flow is unavailable, open a public issue titled `Security contact
requested` without vulnerability details, learner data, credentials, or proof
of concept, and ask the maintainer to arrange a private channel.

Do not open a public issue for a vulnerability that could expose learner data,
execute code, overwrite files, disclose credentials, or bypass workspace
isolation. Include the affected version, reproduction steps, impact, and the
smallest safe proof of concept. Do not include real student records or API keys.

## Security boundaries

- Treat learner memory, review history, uploaded notes, and conversation traces
  as private user data. Keep them out of Git and logs by default.
- Treat downloaded skills, scripts, prompts, and model artifacts as untrusted
  until their source and contents have been reviewed.
- Run agents with the least filesystem and network access required. A Skill is
  instruction content, not a security sandbox.
- Use isolated memory directories for different users. The local JSON helpers
  provide atomic replacement and backups, but not multi-user authorization.
- When a deployment calls an external model provider, disclose that learner
  content leaves the local machine and follow that provider's data policy.

Pedagogical inaccuracies and ordinary bad outputs are quality bugs rather than
security vulnerabilities; report those through a normal GitHub issue after
removing personal data.
