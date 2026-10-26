import os, time, requests, sys, json, re, html, base64
from cryptography.fernet import Fernet

CID = os.environ['GMAIL_CLIENT_ID']
CS = os.environ['GMAIL_CLIENT_SECRET']
RT = os.environ['GMAIL_REFRESH_TOKEN']
RUN_SECONDS = int(os.environ.get('RUN_SECONDS', '280'))
ARCHIVE_KEY = os.environ.get('ARCHIVE_KEY', '')
Q = 'from:surfshark.com in:anywhere'

fernet = Fernet(ARCHIVE_KEY.encode()) if ARCHIVE_KEY else None


def get_token():
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': CID, 'client_secret': CS,
        'refresh_token': RT, 'grant_type': 'refresh_token'
    }, timeout=30)
    r.raise_for_status()
    return r.json()['access_token']


def b64(s):
    s = s.replace('-', '+').replace('_', '/')
    s += '=' * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode('utf-8', 'replace')
    except Exception:
        return ''


def walk(p):
    out = []
    if p.get('body', {}).get('data'):
        out.append(b64(p['body']['data']))
    for x in p.get('parts', []) or []:
        out += walk(x)
    return out


def archive_message(mid, headers):
    """Fetch full message, encrypt it and print ARCHIVE:<token> to the log."""
    r = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages/' + mid,
                     headers=headers, params={'format': 'full'}, timeout=30)
    r.raise_for_status()
    full = r.json()
    hd = {h['name'].lower(): h['value'] for h in full.get('payload', {}).get('headers', [])}
    body = '\n'.join(walk(full.get('payload', {})))
    text = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    text = re.sub(r'\s+', ' ', text).strip()[:20000]
    rec = {
        'id': mid,
        'date': hd.get('date', ''),
        'from': hd.get('from', ''),
        'to': hd.get('to', ''),
        'subject': hd.get('subject', ''),
        'snippet': full.get('snippet', ''),
        'body': text,
    }
    token = fernet.encrypt(json.dumps(rec, ensure_ascii=False).encode('utf-8')).decode('ascii')
    print('ARCHIVE:' + token, flush=True)


at = get_token()
H = {'Authorization': 'Bearer ' + at}
deadline = time.time() + RUN_SECONDS
deleted = 0
print('cleaner started, run_seconds=%s archive=%s' % (RUN_SECONDS, bool(fernet)), flush=True)

while time.time() < deadline:
    try:
        r = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',
                         headers=H, params={'q': Q, 'maxResults': 500}, timeout=30)
        if r.status_code == 401:
            at = get_token(); H = {'Authorization': 'Bearer ' + at}; continue
        data = r.json()
        msgs = data.get('messages', [])
        if not msgs:
            time.sleep(1)
            continue
        for m in msgs:
            if fernet:
                try:
                    archive_message(m['id'], H)
                except Exception as e:
                    print('archive_err', type(e).__name__, str(e)[:160], flush=True)
            d = requests.delete('https://gmail.googleapis.com/gmail/v1/users/me/messages/' + m['id'],
                                headers=H, timeout=30)
            if d.status_code in (200, 204):
                deleted += 1
            elif d.status_code == 401:
                at = get_token(); H = {'Authorization': 'Bearer ' + at}
        time.sleep(1)
    except Exception as e:
        print('err', type(e).__name__, str(e)[:200], flush=True)
        time.sleep(1)

print('deleted_total=%d' % deleted, flush=True)
