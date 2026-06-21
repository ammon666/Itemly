"""
通用参数校验工具。所有业务路由应优先使用这里封装的函数，
以保持校验逻辑统一、可测、可演进。
"""
import re
import html


def require_str(value, min_len=0, max_len=200, strip=True, escape_html=False):
    """校验并返回字符串。不符合要求时抛出 ValueError。"""
    if value is None:
        raise ValueError('内容不能为空')
    s = str(value)
    if strip:
        s = s.strip()
    length = len(s)
    if length < min_len:
        raise ValueError(f'内容长度不得少于 {min_len} 个字符')
    if length > max_len:
        raise ValueError(f'内容长度不得超过 {max_len} 个字符')
    if escape_html:
        s = html.escape(s)
    return s


def require_int(value, min_value=None, max_value=None):
    """校验并返回整数。不符合要求时抛出 ValueError。"""
    try:
        i = int(value)
    except (TypeError, ValueError):
        raise ValueError('必须是整数')
    if min_value is not None and i < min_value:
        raise ValueError(f'不得小于 {min_value}')
    if max_value is not None and i > max_value:
        raise ValueError(f'不得大于 {max_value}')
    return i


def require_int_list(value, min_value=None, max_value=None, dedupe=True):
    """校验并返回整数列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        parts = [x.strip() for x in value.split(',') if x.strip()]
    else:
        try:
            parts = list(value)
        except TypeError:
            raise ValueError('必须是列表或逗号分隔字符串')
    result = []
    for p in parts:
        result.append(require_int(p, min_value, max_value))
    if dedupe:
        seen = set()
        deduped = []
        for x in result:
            if x not in seen:
                seen.add(x)
                deduped.append(x)
        result = deduped
    return result


_USERNAME_RE = re.compile(r'^[A-Za-z0-9_\-\u4e00-\u9fa5]+$')


def require_username(value):
    s = require_str(value, min_len=3, max_len=32)
    if not _USERNAME_RE.match(s):
        raise ValueError('用户名仅允许字母、数字、下划线、中划线和中文')
    return s


_EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')


def require_email(value):
    """校验并返回邮箱地址。不符合要求时抛出 ValueError。"""
    if value is None:
        raise ValueError('邮箱不能为空')
    s = str(value).strip()
    if not s:
        raise ValueError('邮箱不能为空')
    if len(s) > 200:
        raise ValueError('邮箱长度不得超过 200 个字符')
    if not _EMAIL_RE.match(s):
        raise ValueError('邮箱格式不正确')
    return s


_LIKE_ESCAPE_RE = re.compile(r'([%_\\])')


def escape_like(value, escape_char='\\'):
    """将 SQL LIKE 通配符转义。用于用户输入的 keyword 做字面匹配。"""
    if value is None:
        return ''
    return _LIKE_ESCAPE_RE.sub(escape_char + r'\1', str(value))
