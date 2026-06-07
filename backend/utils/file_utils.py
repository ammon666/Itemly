"""
Itemly 文件工具
"""
import os
import uuid
import base64
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_base64_image(base64_data, upload_folder):
    """保存Base64编码的图片"""
    if not base64_data:
        return None

    # 处理data URI格式
    if ',' in base64_data:
        header, base64_data = base64_data.split(',', 1)

    try:
        # 解码Base64
        image_data = base64.b64decode(base64_data)
    except Exception:
        return None

    # 生成唯一文件名
    ext = 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, filename)

    # 保存文件
    try:
        with open(filepath, 'wb') as f:
            f.write(image_data)
        return filename
    except Exception:
        return None


def delete_image(filename, upload_folder):
    """删除图片文件"""
    if not filename:
        return False
    filepath = os.path.join(upload_folder, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False
    return False


def get_file_url(filename, base_url=''):
    """获取文件的访问URL"""
    if not filename:
        return ''
    return f"{base_url}/uploads/{filename}"
