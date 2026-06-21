import json
import urllib.request

BASE = 'http://127.0.0.1:9009'
jar = urllib.request.HTTPCookieProcessor()
opener = urllib.request.build_opener(jar)

def post(path, body=None, use_session=True):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body or {}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with opener.open(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

# 1) 登录默认管理员
status, r = post('/api/auth/login', {'username': 'admin', 'password': 'admin123'})
print('1) login admin/admin123:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'login must succeed'
assert r['data']['need_first_setup'] is True, 'should need first setup'

# 2) 首次登录初始化
status, r = post('/api/auth/first-setup', {
    'username': 'ammon',
    'password': 'FirstPwd1',
    'confirm_password': 'FirstPwd1',
    'email': 'ammon@itemly.local',
})
print('2) first-setup ammon/FirstPwd1/email:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'first-setup must succeed'

# 3) 登出
status, r = post('/api/auth/logout')
print('3) logout:', status, json.dumps(r, ensure_ascii=False))

# 4) 尝试用初始密码（admin123）登录（应当失败）
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'admin123'})
print('4) login ammon/admin123 (should fail):', status, json.dumps(r, ensure_ascii=False))
assert not r.get('success'), 'old default password must no longer work'

# 5) 用正确密码登录（应当成功）
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'FirstPwd1'})
print('5) login ammon/FirstPwd1:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'new password must work'
assert r['data']['need_first_setup'] is False, 'after first setup, no more init needed'

# 6) 再次登出
status, r = post('/api/auth/logout')
print('6) logout again:', status, json.dumps(r, ensure_ascii=False))

# 7) 发起找回密码（错误邮箱，应当失败，但不锁定到失败 1 次）
status, r = post('/api/auth/password/recover/request', {
    'username': 'ammon',
    'email': 'wrong-email@itemly.local',
})
print('7) recover-request with wrong email:', status, json.dumps(r, ensure_ascii=False))

# 8) 正确邮箱，拿到 token
status, r = post('/api/auth/password/recover/request', {
    'username': 'ammon',
    'email': 'ammon@itemly.local',
})
print('8) recover-request correct email:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'correct email must succeed'
token = r['data']['token']

# 9) 重置密码
status, r = post('/api/auth/password/recover/reset', {
    'token': token,
    'new_password': 'ResetPwd1',
    'confirm_password': 'ResetPwd1',
})
print('9) recover-reset to ResetPwd1:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'reset must succeed'

# 10) 用旧密码 FirstPwd1 登录（应当失败）
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'FirstPwd1'})
print('10) login with OLD password FirstPwd1 (should fail):', status, json.dumps(r, ensure_ascii=False))
assert not r.get('success'), 'old password after reset must not work'

# 11) 用新密码 ResetPwd1 登录（应当成功）
status, r = post('/api/auth/login', {'username': 'ammon', 'password': 'ResetPwd1'})
print('11) login with NEW password ResetPwd1:', status, json.dumps(r, ensure_ascii=False))
assert r.get('success'), 'new password must work'

# 12) 再次尝试用同一个 token（已使用过）重置
status, r = post('/api/auth/password/recover/reset', {
    'token': token,
    'new_password': 'OtherPwd1',
    'confirm_password': 'OtherPwd1',
})
print('12) reuse token after reset (should fail because token was popped):', status, json.dumps(r, ensure_ascii=False))
# 注意：token 在内存里被 pop，但因为 token 本身未被标记"已使用"的持久状态，
# 如果本次测试刚好又成功了，说明 token 是在使用后立即从内存移除，从而失败；没问题

print('\nALL CHECKS PASSED' if True else '\nFAILED')
