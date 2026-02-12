"""
用户提示词配置功能测试脚本
"""
import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1/user-prompt-config"


async def test_api():
    """测试用户提示词配置API"""

    # 测试数据
    test_config = {
        "config_name": f"测试配置_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "system_config": "这是一个系统级别的描述",
        "table_notes": ["表级别的注意事项1", "表级别的注意事项2"],
        "field_notes": ["字段级别的使用方式1", "字段级别的使用方式2"],
        "config_type": 2  # 自定义
    }

    async with httpx.AsyncClient() as client:
        print("🧪 开始测试用户提示词配置功能...")

        try:
            # 1. 测试创建配置
            print("\n1. 测试创建配置...")
            response = await client.post(BASE_URL, json=test_config)
            if response.status_code == 201:
                created_config = response.json()
                print(f"✅ 创建成功: {created_config['data']['config_name']}")
                config_id = created_config['data']['id']
            else:
                print(f"❌ 创建失败: {response.status_code} - {response.text}")
                return

            # 2. 测试获取单个配置
            print(f"\n2. 测试获取配置 (ID: {config_id})...")
            response = await client.get(f"{BASE_URL}/{config_id}")
            if response.status_code == 200:
                fetched_config = response.json()
                print(f"✅ 获取成功: {fetched_config['data']['config_name']}")
            else:
                print(f"❌ 获取失败: {response.status_code} - {response.text}")
                return

            # 3. 测试更新配置
            print(f"\n3. 测试更新配置...")
            update_data = {
                "system_config": "更新后的系统级别描述",
                "config_type": 1  # 修改为默认
            }
            response = await client.put(f"{BASE_URL}/{config_id}", json=update_data)
            if response.status_code == 200:
                updated_config = response.json()
                print(f"✅ 更新成功: 配置类型改为 {updated_config['data']['config_type']}")
            else:
                print(f"❌ 更新失败: {response.status_code} - {response.text}")

            # 4. 测试获取配置列表
            print(f"\n4. 测试获取配置列表...")
            response = await client.get(f"{BASE_URL}/")
            if response.status_code == 200:
                configs_list = response.json()
                print(f"✅ 获取列表成功: 共 {configs_list['total']} 条记录")
            else:
                print(f"❌ 获取列表失败: {response.status_code} - {response.text}")

            # 5. 测试根据名称查询
            print(f"\n5. 测试根据名称查询配置...")
            response = await client.get(f"{BASE_URL}/name/{test_config['config_name']}")
            if response.status_code == 200:
                found_config = response.json()
                print(f"✅ 根据名称查询成功: {found_config['data']['config_name']}")
            else:
                print(f"❌ 根据名称查询失败: {response.status_code} - {response.text}")

            # 6. 测试根据类型查询
            print(f"\n6. 测试根据类型查询配置 (类型: 1)...")
            response = await client.get(f"{BASE_URL}/type/1")
            if response.status_code == 200:
                type_configs = response.json()
                print(f"✅ 根据类型查询成功: 找到 {type_configs['total']} 条记录")
            else:
                print(f"❌ 根据类型查询失败: {response.status_code} - {response.text}")

            # 创建额外配置用于批量删除测试
            print(f"\n7. 创建额外配置用于批量删除测试...")
            extra_configs = []
            for i in range(3):
                extra_config = {
                    "config_name": f"批量删除测试_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "system_config": f"测试配置{i}",
                    "config_type": 2
                }
                response = await client.post(BASE_URL, json=extra_config)
                if response.status_code == 201:
                    config_data = response.json()
                    extra_configs.append(config_data['data']['id'])
                    print(f"   ✅ 创建额外配置 {i+1}: ID {config_data['data']['id']}")

            # 8. 测试批量删除
            if extra_configs:
                print(f"\n8. 测试批量删除配置...")
                batch_data = {"ids": extra_configs}
                response = await client.post(f"{BASE_URL}/batch-delete", json=batch_data)
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 批量删除成功: 删除了 {result['deleted_count']} 个配置")
                else:
                    print(f"❌ 批量删除失败: {response.status_code} - {response.text}")

            # 9. 测试删除原始配置
            print(f"\n9. 测试删除原始配置...")
            response = await client.delete(f"{BASE_URL}/{config_id}")
            if response.status_code == 200:
                deleted_config = response.json()
                print(f"✅ 删除成功: {deleted_config['data']['config_name']}")
            else:
                print(f"❌ 删除失败: {response.status_code} - {response.text}")

            print("\n🎉 所有测试完成！")

        except httpx.ConnectError:
            print("❌ 无法连接到服务器，请确保应用正在运行 (http://localhost:8000)")
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {str(e)}")


if __name__ == "__main__":
    print("用户提示词配置功能测试")
    print("请确保应用正在运行: python run.py")
    print("=" * 50)

    response = input("是否继续测试? (y/n): ")
    if response.lower() in ['y', 'yes', '是']:
        asyncio.run(test_api())