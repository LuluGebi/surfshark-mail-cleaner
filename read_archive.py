# -*- coding: utf-8 -*-
import sys, subprocess, re
from cryptography.fernet import Fernet
if len(sys.argv) < 2:
    print('usage: python read_archive.py <run_id>'); sys.exit(2)
KEY = open('../_surfshark_archive_key.txt', encoding='utf-8').read().strip()
out = subprocess.check_output(
    ['gh', 'run', 'view', sys.argv[1], '--repo', 'LuluGebi/surfshark-mail-cleaner', '--log'],
    text=True, encoding='utf-8', errors='replace'
)
n = 0
for m in re.finditer(r'ARCHIVE:([A-Za-z0-9_=-]+)', out):
    try:
        print(Fernet(KEY).decrypt(m.group(1).encode()).decode('utf-8'))
        print('---')
        n += 1
    except Exception as e:
        print('decrypt_err', e)
print('archived_messages=%d' % n)
