"""Loopback-only research API, revision studio and production frontend."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import secrets
from pathlib import Path
from urllib.parse import unquote, urlsplit, quote

from .data import Repository
from .studio import Studio, Conflict

ROOT = Path(__file__).resolve().parents[1]


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, repository, **kwargs):
        self.repository = repository
        super().__init__(*args, **kwargs)

    def _send(self, status, data, content_type='application/json; charset=utf-8', filename=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-store')
        if filename:
            disposition = 'inline' if content_type == 'application/pdf' else 'attachment'
            self.send_header('Content-Disposition', f"{disposition}; filename*=UTF-8''{quote(filename)}")
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError): pass

    def _json(self, status, value):
        self._send(status, json.dumps(value, ensure_ascii=False).encode('utf-8'))

    def _local(self):
        try:
            host = urlsplit('//'+self.headers.get('Host', '')).hostname
            origin = self.headers.get('Origin')
            return host in ('127.0.0.1','localhost') and (not origin or urlsplit(origin).hostname in ('127.0.0.1','localhost'))
        except ValueError: return False

    def _file(self, path):
        mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        self._send(200,path.read_bytes(),mime,path.name)

    def do_POST(self):
        if not self._local() or not secrets.compare_digest(self.headers.get('X-Workbench-Token',''),self.server.write_token):
            return self._json(403,{'error':'Local write token required'})
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            return self._json(415,{'error':'JSON required'})
        try:
            size = int(self.headers.get('Content-Length','0'))
            if size <= 0 or size > 180000: return self._json(413,{'error':'Invalid request size'})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body,dict): raise ValueError('JSON object required')
            parts = unquote(urlsplit(self.path).path).strip('/').split('/')
            if parts[:2] != ['api','runs']: raise KeyError('Unknown operation')
            if len(parts)==4 and parts[3]=='studio':
                return self._json(201,self.server.studio.save(parts[2],body.get('sections'),body.get('base_revision')))
            if len(parts)==6 and parts[3]=='studio' and parts[5]=='jobs':
                return self._json(202,self.server.studio.start(parts[2],parts[4],body.get('kind'),body.get('profile','color')))
            raise KeyError('Unknown operation')
        except Conflict as error: self._json(409,{'error':str(error)})
        except KeyError: self._json(404,{'error':'Unknown run or revision'})
        except (ValueError,TypeError,UnicodeError) as error: self._json(400,{'error':str(error)})
        except OSError: self._json(503,{'error':'Local revision files unavailable'})

    def do_GET(self):
        if not self._local():
            return self._json(403, {'error': 'Local requests only'})
        path = unquote(urlsplit(self.path).path)
        parts = path.strip('/').split('/')
        if any(p in ('.', '..') or '\\' in p for p in parts):
            return self._json(404, {'error': 'Not found'})
        try:
            if path == '/api/session': return self._json(200,{'token':self.server.write_token})
            if path == '/api/discovery':
                from .discovery import payload
                return self._json(200,payload(self.repository))
            if path == '/api/upgrade':
                from .upgrade import payload
                return self._json(200,payload(self.repository))
            if parts[:3]==['api','upgrade','files'] and len(parts)==4:
                from .upgrade import file_path
                return self._file(file_path(self.repository,parts[3]))
            if path == '/api/runs': return self._json(200, self.repository.runs())
            if parts[:2] == ['api', 'runs'] and len(parts) >= 3:
                run_id = parts[2]
                if len(parts) == 3: return self._json(200, self.repository.overview(run_id))
                if len(parts) == 4 and parts[3] == 'cases': return self._json(200, self.repository.cases(run_id))
                if len(parts)==4 and parts[3]=='analysis':
                    from research.error_analysis import analyze_errors
                    return self._json(200,analyze_errors(self.repository._run(run_id)))
                if len(parts)>=4 and parts[3]=='studio':
                    studio=self.server.studio
                    if len(parts)==4: return self._json(200,studio.list(run_id))
                    if len(parts)==5: return self._json(200,studio.get(run_id,parts[4]))
                    if len(parts)==6 and parts[5]=='latex': return self._file(studio.asset(run_id,parts[4],'latex'))
                    if len(parts)==7 and parts[5]=='jobs': return self._json(200,studio.job(run_id,parts[4],parts[6]))
                    if len(parts)==9 and parts[5]=='jobs' and parts[7]=='files': return self._file(studio.job_asset(run_id,parts[4],parts[6],parts[8]))
                if len(parts) == 5 and parts[3] == 'files':
                    artifact = self.repository.artifact_path(run_id, parts[4])
                    mime = mimetypes.guess_type(artifact.name)[0] or 'application/octet-stream'
                    return self._send(200, artifact.read_bytes(), mime, artifact.name)
            static = (self.repository.root/'frontend/dist').resolve()
            relative = 'index.html' if path == '/' else path.removeprefix('/')
            # No SPA fallback for unknown files: credentials are never served.
            file = (static/relative).resolve()
            if not file.is_relative_to(static) or (path != '/' and not path.startswith('/assets/')) or not file.is_file():
                return self._json(404, {'error': 'Not found. Build frontend first if / is missing.'})
            mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
            self._send(200, file.read_bytes(), mime)
        except KeyError:
            self._json(404, {'error': 'Run or artifact not found'})
        except (OSError, ValueError, TypeError):
            self._json(503, {'error': 'Local artifact unavailable or invalid; inspect source files.'})


def make_server(repository=None, port=8765):
    repository=repository or Repository(ROOT)
    server=ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, repository=repository))
    server.write_token=secrets.token_urlsafe(32)
    server.studio=Studio(repository)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with make_server(port=args.port) as server:
        print(f'Research Workbench: http://127.0.0.1:{server.server_port}', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass


if __name__ == '__main__': main()
