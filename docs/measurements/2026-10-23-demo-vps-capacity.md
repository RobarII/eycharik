# Demo VPS capacity

- Date: 2026-10-23
- Host: the `vps` alias, Ubuntu 22.04.5 LTS, Docker 29.5.3, Compose v5.1.4
- Commit: `91bbfb2`
- Command:

```bash
ssh vps 'nproc; free -m; df -h /; docker --version; docker compose version; . /etc/os-release && echo "$PRETTY_NAME"'
```

- Output:

```text
1
               total        used        free      shared  buff/cache   available
Mem:             921         377          81           2         461         379
Swap:            511          70         441
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        20G  9.9G  9.4G  52% /
Docker version 29.5.3, build d1c06ef
Docker Compose version v5.1.4
Ubuntu 22.04.5 LTS
```

The host has one vCPU, 921 MiB of RAM, 511 MiB of swap, and 9.4 GiB free on `/`. That is enough
for the demo stack with the compose memory limits, but not for a pilot that stores real personal
data: it has no headroom for a second API replica, a local reranker, or a large corpus ingest.
The deployment runbook records the same constraint.

The host is in the Netherlands, so the demo does not satisfy the localisation requirement of
152-ФЗ for Russian personal data. Treat it as a demo with synthetic or public data only.
