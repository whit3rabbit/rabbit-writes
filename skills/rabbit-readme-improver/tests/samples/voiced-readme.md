# Portcheck

Portcheck tells you which process is holding a port — and then offers to kill it. It exists because `lsof -i :8080` is four flags too many to remember at the moment you need it.

## Install

```bash
brew install portcheck
```

## Usage

```bash
portcheck 8080
```

Furthermore, the tool prints the command line of the holding process; this is usually enough to tell a stale dev server from something you actually wanted running.

At the end of the day, the point is to stop you from killing the wrong PID. Portcheck asks before it signals anything, and it never signals PID 1.

## License

MIT. See [LICENSE](LICENSE).
