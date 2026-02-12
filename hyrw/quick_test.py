"""
快速测试用户提示词配置功能
"""
import asyncio
import json
from datetime import datetime
from app.services.user_prompt_config import user_prompt_config_service
from app.schemas.user_prompt_config import UserPromptConfigCreate, UserPromptConfigUpdate
from app.core.database import SessionLocal


async def quick_test():
    """快速测试用户提示词配置的完整功能"""

    test_data = UserPromptConfigCreate(
        config_name=f"快速测试_{datetime.now().strftime('%H%M%S')}",
        system_config="这是一个测试系统的描述",
        table_notes=["用户表包含私人信息", "订单表需要聚合查询"],
        field_notes=["ID字段支持关联", "金额字段可做统计"],
        config_type=2
    )

    async with SessionLocal() as db:
        print("🚀 开始快速测试...")

        try:
            # 1. 创建配置
            print("\n1️⃣ 创建配置...")
            config = await user_prompt_config_service.create(db, obj_in=test_data)
            print(f"✅ 创建成功: ID={config.id}, 名称={config.config_name}")
            print(f"   表注释: {config.table_notes}")
            print(f"   字段注释: {config.field_notes}")

            # 2. 获取单个配置
            print(f"\n2️⃣ 获取配置 ID={config.id}...")
            fetched = await user_prompt_config_service.get_by_id(db, id=config.id)
            print(f"✅ 获取成功: 系统描述={fetched.system_config}")

            # 3. 更新配置
            print(f"\n3️⃣ 更新配置 ID={config.id}...")
            update_data = UserPromptConfigUpdate(
                system_config="更新后的系统描述",
                config_type=1,
                table_notes=["新的表注释1", "新的表注释2"]
            )
            updated = await user_prompt_config_service.update(db, id=config.id, obj_in=update_data)
            print(f"✅ 更新成功: 类型={updated.config_type}, 描述={updated.system_config}")
            print(f"   表注释: {updated.table_notes}")

            # 4. 获取列表
            print(f"\n4️⃣ 获取配置列表...")
            configs, total = await user_prompt_config_service.get_multi(db, limit=10)
            print(f"✅ 获取列表成功: 共 {total} 条记录")

            # 5. 根据名称查询
            print(f"\n5️⃣ 根据名称查询: {config.config_name}...")
            found = await user_prompt_config_service.get_by_name(db, config_name=config.config_name)
            print(f"✅ 查询成功: ID={found.id}")

            # 6. 根据类型查询
            print(f"\n6️⃣ 根据类型查询: type=1...")
            type_configs = await user_prompt_config_service.get_by_type(db, config_type=1)
            print(f"✅ 查询成功: 找到 {len(type_configs)} 条记录")

            # 7. 删除配置
            print(f"\n7️⃣ 删除配置 ID={config.id}...")
            deleted = await user_prompt_config_service.delete(db, id=config.id)
            print(f"✅ 删除成功: {deleted.config_name}")

            print("\n🎉 所有测试通过！功能正常工作！")

        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(quick_test())