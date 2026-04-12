#!/usr/bin/env node
// Google OAuth トークン自動更新スクリプト
// Claude Code の UserPromptSubmit フックから呼び出される

const fs = require('fs');
const path = require('path');
const https = require('https');
const os = require('os');

// __dirname ベースで動的にパスを解決（ポータブル）
const SETTINGS_PATH = path.join(__dirname, '..', 'settings.json');
const GDRIVE_CREDS_PATH = path.join(os.homedir(), '.gdrive-server-credentials.json');
const REFRESH_MARGIN_MS = 5 * 60 * 1000; // 期限切れ5分前に更新

function refreshToken(clientId, clientSecret, refreshToken) {
  return new Promise((resolve, reject) => {
    const body = new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      refresh_token: refreshToken,
      grant_type: 'refresh_token',
    }).toString();

    const req = https.request({
      hostname: 'oauth2.googleapis.com',
      path: '/token',
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.access_token) resolve(parsed);
          else reject(new Error(data));
        } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  if (!fs.existsSync(SETTINGS_PATH)) return;

  const settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8'));
  const sheetsEnv = settings.mcpServers?.google_sheets?.env;
  if (!sheetsEnv) return;

  const expiry = new Date(sheetsEnv.GOOGLE_SHEETS_TOKEN_EXPIRY).getTime();
  const now = Date.now();

  if (expiry - now > REFRESH_MARGIN_MS) return; // まだ有効

  const clientId = sheetsEnv.GOOGLE_SHEETS_CLIENT_ID;
  const clientSecret = sheetsEnv.GOOGLE_SHEETS_CLIENT_SECRET;
  const refToken = sheetsEnv.GOOGLE_SHEETS_REFRESH_TOKEN;

  if (!clientId || !clientSecret || !refToken) return;

  try {
    const result = await refreshToken(clientId, clientSecret, refToken);
    const newExpiry = new Date(now + result.expires_in * 1000).toISOString();

    settings.mcpServers.google_sheets.env.GOOGLE_SHEETS_ACCESS_TOKEN = result.access_token;
    settings.mcpServers.google_sheets.env.GOOGLE_SHEETS_TOKEN_EXPIRY = newExpiry;
    fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2));

    if (fs.existsSync(GDRIVE_CREDS_PATH)) {
      const creds = JSON.parse(fs.readFileSync(GDRIVE_CREDS_PATH, 'utf8'));
      creds.access_token = result.access_token;
      creds.expiry_date = now + result.expires_in * 1000;
      fs.writeFileSync(GDRIVE_CREDS_PATH, JSON.stringify(creds));
    }

    process.stderr.write('[token-refresh] Google トークンを更新しました\n');
  } catch (e) {
    process.stderr.write(`[token-refresh] 更新失敗: ${e.message}\n`);
  }
}

main();
