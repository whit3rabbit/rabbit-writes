<div align="center">
  <img src="https://example.com/logo.png" alt="Tinylock logo" width="120" />
  <h1>Tinylock</h1>
</div>

Tinylock is a file-based advisory lock for shell scripts. It exists because `flock` is missing on macOS and every workaround people paste into their scripts leaks the lock when the script dies.

<p align="center">
  <a href="https://pypi.org/project/tinylock/"><img src="https://img.shields.io/pypi/v/tinylock" alt="PyPI"/></a>
  <a href="https://github.com/example/tinylock/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/example/tinylock/ci.yml" alt="Build"/></a>
</p>

## Install

```bash
pip install tinylock
```

Then wrap anything that must not run twice:

```bash
tinylock /tmp/backup.lock -- ./backup.sh
```

If another process holds the lock, `tinylock` exits 75 and prints the holding PID. Nothing else happens.

## How it works

The lock is a directory, not a file. `mkdir` is atomic on every POSIX filesystem worth using, including NFS, which is where the usual `O_EXCL` trick quietly stops being atomic.

A holder writes its PID into the directory. A would-be holder that finds a stale PID (no such process) removes the directory and retries once. That single retry is deliberate: a loop here turns a crash into a thundering herd.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `TINYLOCK_TIMEOUT` | `0` | Seconds to wait for the lock. Zero fails immediately |
| `TINYLOCK_STALE_AFTER` | `3600` | Age past which a lock with a dead PID is reclaimed |

| Style | Share of corpus links |
|---|---|
| Inline `[text](url)` | 96.8% |
| Reference `[text][ref]` | 0.2% |

## Benchmarks

Acquiring an uncontended lock takes about 0.4 ms on an SSD, roughly 12x faster than spawning `flock` through a shell. That number measures the syscalls only, not the process spawn, and it varies with filesystem: on NFS the same acquire runs closer to 4 ms.

## Testing

```bash
python3 -m pytest
```

## Contributing

Bug reports and patches are welcome. Read [the contributing guide](CONTRIBUTING.md) first. This paragraph runs deliberately long so the line-number regression has something to anchor on, well past the sixty word threshold the checker uses, sitting below several fenced code blocks and a markdown table so that any change which strips those spans instead of blanking them will shift the reported line and fail the assertion below.

## License

MIT. See [LICENSE](LICENSE).
