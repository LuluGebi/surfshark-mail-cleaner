import os, time, requests, sys

CID = os.environ['GMAIL_CLIENT_ID']
CS = os.environ['GMAIL_CLIENT_SECRET']
RT = os.environ['GMAIL_REFRESH_TOKEN']
RUN_SECONDS = int(os.environ.get('RUN_SECONDS', '280'))
Q = 'from:surfshark.com in:anywhere'

def get_token():
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': CID, 'client_secret': CS,
        'refresh_token': RT, 'grant_type': 'refresh_token'
    }, timeout=30)
    r.raise_for_status()
    return r.json()['access_token']

at = get_token()
H = {'Authorization': 'Bearer ' + at}
deadline = time.time() + RUN_SECONDS
deleted = 0
print('cleaner started, run_seconds=%s' % RUN_SECONDS, flush=True)

while time.time() < deadline:
    try:
        r = requests.get('https://gmail.googleapis.com/gmail/v1/users/me/messages',
                         headers=H, params={'q': Q, 'maxResults': 500}, timeout=30)
        if r.status_code == 401:
            at = get_token(); H = {'Authorization': 'Bearer ' + at}; continue
        data = r.json()
        msgs = data.get('messages', [])
        if not msgs:
            time.sleep(5)
            continue
        for m in msgs:
            d = requests.delete('https://gmail.googleapis.com/gmail/v1/users/me/messages/' + m['id'],
                                headers=H, timeout=30)
            if d.status_code in (200, 204):
                deleted += 1
            elif d.status_code == 401:
                at = get_token(); H = {'Authorization': 'Bearer ' + at}
        time.sleep(2)
    except Exception as e:
        print('err', type(e).__name__, str(e)[:200], flush=True)
        time.sleep(5)

print('deleted_total=%d' % deleted, flush=True)
