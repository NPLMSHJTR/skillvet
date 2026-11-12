# Security

`skillvet` is a static analyser. It reads files and prints a report. It does not
execute skill scripts, does not make network requests, and does not write to
disk.

That is a design constraint, not a coincidence. A tool whose job is to inspect
untrusted skill directories should not be a way to run them.

## What the tool does on disk

- Opens and reads `SKILL.md` files found under the paths you pass.
- Lists `scripts/` directories to check for unreferenced files. It reads their
  names, never their contents.
- Resolves relative link targets to check they exist. Symlinks are followed by
  the normal path resolution rules of the operating system.

## What it does not do

- No `subprocess` calls in the core checker.
- No `eval`, `exec`, or dynamic imports of anything from a skill directory.
- No network access.
- No writes. The only file the CLI writes is whatever your shell redirects its
  output to.

## A note on what a skill can do

A `SKILL.md` file is instructions for an AI agent. The agent reads them and then
acts, with whatever permissions that agent has. This means:

> A malicious skill does not need an exploit. It needs permission.

`skillvet` checks structure, not intent. It cannot tell you whether a skill's
instructions are safe to follow, and it does not try. A skill that passes all 22
rules may still instruct an agent to delete files, exfiltrate data, or run
destructive commands.

Treat a skill from an untrusted source the same way you would treat a shell
script from an untrusted source: read it before you run it.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainer. Do
not open a public issue for anything that could be exploited.

Useful reports include the input that triggers the problem, the actual behaviour,
and the expected behaviour. This tool parses untrusted text, so the interesting
failure modes are things like catastrophic regex backtracking, unbounded memory
use on a large file, and path traversal through a crafted link target.