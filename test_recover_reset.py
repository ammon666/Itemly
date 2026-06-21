import json
import urllib.request

BASE = 'http://127.0.0.1:9009'
jar = urllib.request.HTTPCookieProcessor()
opener = urllib.request.build_opener(jar)

def post(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body or {}).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with opener.open(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

# 1) 请求找回密码（先用已设置邮箱的用户）
status, r = post('/api/auth/password/recover/request', {'username': 'ammon', 'email': 'test@itemly.local'})
print('recover request:', status, r)
token = r.get('data', {}).get('token') if r.get('success') else None

# 2) 重置密码
status, r = post('/api/auth/password/recover/reset', {'token': token, 'new_password': 'NewResetPass1', 'confirm_password': 'NewResetPass1'})
print('recover reset:', status, r)

# 3) 用新密码登录
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'NewResetPass1'})
print('login with new password:', status, r)

# 4) 用旧密码登录（应当失败）
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'admin123'})
print('login with OLD password admin123 (expect fail):', status, r)
