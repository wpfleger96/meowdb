import { execFileSync } from 'child_process';
import { mkdirSync, rmSync } from 'fs';
import path from 'path';

import { DATA_DIR } from './playwright.config';

export default function globalSetup() {
  rmSync(DATA_DIR, { force: true, recursive: true });
  mkdirSync(DATA_DIR, { recursive: true });

  execFileSync('uv', ['run', 'python', 'ui/seed.py'], {
    cwd: path.resolve(__dirname, '..'),
    env: { ...process.env, MEOWDB_DATA_DIR: DATA_DIR },
    stdio: 'inherit',
  });
}
