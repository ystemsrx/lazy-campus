"""Migrate worker skills text to skill_tags (worker_category_skills association)."""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine
from app.models.task import TaskCategory
from app.models.user import WorkerProfile, worker_skill_tags

SKILL_TO_CATEGORY_MAP = {
    'Python编程': '技术服务',
    'Java编程': '技术服务',
    '数据分析': '技术服务',
    '网站开发': '技术服务',
    '前端开发': '技术服务',
    'Vue.js': '技术服务',
    'React': '技术服务',
    'UI设计': '技术服务',
    'Spring Boot': '技术服务',
    '数据库': '技术服务',
    '平面设计': '技术服务',
    'Logo设计': '技术服务',
    '海报设计': '技术服务',
    '摄影摄像': '活动协助',
    '视频剪辑': '技术服务',
    '舞台角色': '活动协助',
    '英语翻译': '文案写作',
    '文案撰写': '文案写作',
    'PPT制作': '文案写作',
    '高等数学': '学习辅导',
    '微积分': '学习辅导',
    '线性代数': '学习辅导',
    '大学物理': '学习辅导',
    '高中数学课程': '学习辅导',
    '高数辅导': '学习辅导',
    '数学辅导': '学习辅导',
    '搬运帮忙': '跑腿代办',
    '快递代取': '跑腿代办',
    '校园外卖': '跑腿代办',
    '活动指导': '活动协助',
    '礼仪': '活动协助',
    '营销策划': '活动协助',
    '物理辅导': '学习辅导',
    '力学分析': '学习辅导',
    '音乐制作': '活动协助',
    '吉他教学': '学习辅导',
    '乐谱整理': '活动协助',
    '健身指导': '陪伴服务',
    '陪跑': '陪伴服务',
    '营养建议': '生活服务',
}


def migrate():
    with Session(engine) as db:
        categories = {c.name: c.id for c in db.query(TaskCategory).all()}
        print(f'Available categories: {categories}')

        profiles = db.query(WorkerProfile).filter(WorkerProfile.skills.isnot(None), WorkerProfile.skills != '').all()
        print(f'Profiles to migrate: {len(profiles)}')

        for p in profiles:
            skills_text = p.skills.strip()
            skill_list = [s.strip() for s in skills_text.replace(',', '、').replace('，', '、').split('、') if s.strip()]
            mapped_cat_ids = set()

            for skill in skill_list:
                cat_name = SKILL_TO_CATEGORY_MAP.get(skill)
                if cat_name and cat_name in categories:
                    mapped_cat_ids.add(categories[cat_name])

            if not mapped_cat_ids:
                for skill in skill_list:
                    for cat_name, cat_id in categories.items():
                        if skill in cat_name or cat_name in skill:
                            mapped_cat_ids.add(cat_id)
                            break

            if not mapped_cat_ids:
                print(f'  profile {p.id} (user {p.user_id}): no mapping for skills "{skills_text}"')
                continue

            tag_ids = list(mapped_cat_ids)[:5]
            tags = db.query(TaskCategory).filter(TaskCategory.id.in_(tag_ids)).all()
            p.skill_tags = tags
            p.skills = '、'.join(t.name for t in tags)
            print(f'  profile {p.id} (user {p.user_id}): mapped to {[t.name for t in tags]}')

        db.commit()
        print('Migration complete!')


if __name__ == '__main__':
    migrate()
