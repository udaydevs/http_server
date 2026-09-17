# Uday HTTP Server

A small HTTP server built from scratch with Python TCP sockets. It is a learning project that parses basic HTTP requests and serves local files.

## Run it

You only need Python 3:

```bash
python3 http/server.py
```

The server listens on port `8000`. Open [http://localhost:8000](http://localhost:8000) in a browser to see the included sample page.

## Current status

The server can currently serve local files with `GET`. Support for `HEAD`, `POST`, other HTTP methods, and more complete error handling is still a work in progress.

Files are served relative to the project directory. The root URL serves `http/index.html`.

## Project layout

```text
http/server.py   Server implementation
http/index.html  Default page
client.py        Simple TCP client example
```

This is intentionally minimal and is not intended for production use.
