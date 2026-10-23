# Reaching a blocked model provider

A measurement is only reproducible if the path between this machine and the provider is known. This
runbook covers the case where the path is not the open internet: the provider is unreachable from
the workstation but reachable from a machine we already control.

## The symptom

Every call to the vendor fails at the transport layer, before any credential is checked:

```
curl -sI https://openrouter.ai/
HTTP/2 403
```

An unauthenticated request to the vendor's homepage answering `403 Access denied by security policy`
is a network filter, not a key problem. Do not rotate the key: `GET /api/v1/key` fails the same way
without a key at all, and the same key works from any other host.

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://openrouter.ai/api/v1/models   # 403 here
ssh vps 'curl -s -o /dev/null -w "%{http_code}\n" https://openrouter.ai/api/v1/models'  # 200 there
```

## The tunnel

One SSH host block turns the VPS into a SOCKS5 proxy on loopback. The block lives in `~/.ssh/config`,
not in this repository, because it describes this workstation and not the product:

```
Host openrouter-tunnel
    HostName <vps-address>
    User root
    IdentityFile ~/.ssh/id_ed25519_vps_<provider>
    IdentitiesOnly yes
    DynamicForward 127.0.0.1:1080
    ControlMaster auto
    ControlPath ~/.ssh/cm-tunnel-%r@%h:%p
    ControlPersist 8h
    ServerAliveInterval 15
    ServerAliveCountMax 3
    ExitOnForwardFailure yes
```

Use a `ControlPath` that no other host shares. An existing master connection happily accepts the new
session and then ignores `DynamicForward`, which looks like a dead proxy with a live SSH connection.

```bash
ssh -f -N openrouter-tunnel
curl -s --proxy socks5h://127.0.0.1:1080 -o /dev/null -w '%{http_code}\n' \
  https://openrouter.ai/api/v1/models          # 200

ssh -S ~/.ssh/cm-tunnel-root@<vps-address>:22 -O exit openrouter-tunnel   # stop
```

`ControlPersist 8h` keeps the tunnel alive between commands, so a long eval run does not need a
background process of its own.

## Running the product through it

`httpx` reads `HTTPS_PROXY` from the environment when `trust_env` is on, which is the default for the
client the container builds. `socks5h` resolves names on the proxy side, so no DNS lookup leaks
around the tunnel. SOCKS support needs the `socksio` package, which is a dev dependency.

```bash
HTTPS_PROXY=socks5h://127.0.0.1:1080 make eval
HTTPS_PROXY=socks5h://127.0.0.1:1080 make ingest
```

Nothing in `settings.py` changes. Proxy configuration is a property of the shell, not of the
product: a deployment behind an egress proxy sets the same variable for the process and the code
does not need to know.

## What a measurement must say

A report produced through the tunnel records it in the environment line, because latency measured
over a relayed connection is not the latency a user sees:

- a `p95_latency_ms` breach under a tunnel is not evidence about the latency budget ([ADR 0009](../decisions/0009-latency-budget.md));
- `recall`, `leak_rate`, and the answer gates are unaffected: the vectors and the prompt are the same;
- if the tunnel drops mid-run, the run fails with `case_errors`, and that number must be zero before
  the report is quoted.

## Failure modes seen in practice

| Symptom | Cause | Fix |
|---|---|---|
| `Malformed reply from SOCKS server` | tunnel died between commands | restart the master with `-O exit` then `ssh -f -N` |
| `429` from a free rerank endpoint | burst limit, not the tunnel | rerank retries with 2 s and 6 s pauses; the run continues on the fused order if all fail |
| `No route to host` | the VPS itself is down | wait, or pick another host; the tunnel cannot repair a dead relay |
| every call `403` again | the filter moved or the tunnel is bypassed | check `HTTPS_PROXY` is exported in the same shell as the command |
