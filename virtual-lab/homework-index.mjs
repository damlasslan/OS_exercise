// Static entry point for the no-login homework (deployed as index.mjs of the Neon function).
// It serves only the homework page and the simulation engine: no API, no database, no student data on the server.
import {readFile} from 'node:fs/promises';

const files = new Map([['/', 'homework.html'], ['/homework', 'homework.html'], ['/engine.mjs', 'engine.mjs']]);

export default {async fetch(req) {
  const name = files.get(new URL(req.url).pathname);
  if (!name) return new Response('Not found', {status: 404});
  return new Response(await readFile(new URL(name, import.meta.url)), {headers: {
    'Content-Type': name.endsWith('.html') ? 'text/html; charset=utf-8' : 'text/javascript',
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'no-cache',
    'Content-Security-Policy': "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'"
  }});
}};
