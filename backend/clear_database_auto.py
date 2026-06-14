"""
清空数据库中的所有数据（保留表结构）- 自动执行版本
"""
import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'itemly.db')


def clear_all_data():
    """清空所有表的数据"""
    if not os.path.exists(DATABASE_PATH):
        print(f"数据库文件不存在: {DATABASE_PATH}")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"找到 {len(tables)} 个表: {', '.join(tables)}")
        
        # 禁用外键约束（避免删除顺序问题）
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # 清空每个表
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"✓ 已清空表: {table}")
        
        # 重置自增ID
        cursor.execute("DELETE FROM sqlite_sequence")
        print("✓ 已重置所有自增ID")
        
        conn.commit()
        print("\n✅ 数据库清空完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 清空数据库失败: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 50)
    print("警告：此操作将清空数据库中的所有数据！")
    print("=" * 50)
    print("\n开始清空...")
    clear_all_data()
