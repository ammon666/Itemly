# 路由模块初始化
from routes.auth import auth_bp
from routes.items import items_bp
from routes.categories import categories_bp
from routes.attributes import attributes_bp
from routes.stats import stats_bp

__all__ = ['auth_bp', 'items_bp', 'categories_bp', 'attributes_bp', 'stats_bp']