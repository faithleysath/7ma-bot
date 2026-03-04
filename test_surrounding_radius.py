import asyncio
import random
import math
from typing import Any, Literal, cast

# 假设你的 SDK 类名为 SevenMaClient
from sevenma_sdk import SevenMaClient

# 学校选区边界 (Lon, Lat)
BOUNDS = {
    "min_lon": 118.705971,
    "max_lon": 118.728082,
    "min_lat": 32.197149,
    "max_lat": 32.207802
}

# 手动配置："danche"(只看单车) 或 "zhuli"(只看助力车)
VEHICLE_MODE: Literal["danche", "zhuli"] = "zhuli"

def get_random_start_point() -> tuple[float, float]:
    """在选区边界内随机生成一个坐标点作为起点"""
    lon = random.uniform(BOUNDS["min_lon"], BOUNDS["max_lon"])
    lat = random.uniform(BOUNDS["min_lat"], BOUNDS["max_lat"])
    return lat, lon

def get_destination_point(lat: float, lon: float, distance_m: float, bearing_deg: float = 0.0) -> tuple[float, float]:
    """
    根据给定的经纬度、距离(米)和方位角(度)，计算目标经纬度。
    bearing_deg: 0为正北，90为正东，180为正南，270为正西。
    """
    R = 6378137.0  # 地球平均半径(米)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)
    angular_distance = distance_m / R

    lat_out_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )
    
    lon_out_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat_out_rad)
    )

    return math.degrees(lat_out_rad), math.degrees(lon_out_rad)

def check_car_in_response(target_car_id: int, cars_data: Any) -> bool:
    """检查目标车辆是否存在于 API 返回的数据中（按配置车型）"""
    for car in get_cars_by_mode(cars_data):
        car_id_obj = car.get("id")
        if car_id_obj is None:
            continue
        try:
            current_id = int(car_id_obj)
        except (TypeError, ValueError):
            continue
        if current_id == target_car_id:
            return True
    return False


def get_cars_by_mode(cars_data: Any) -> list[dict[str, Any]]:
    """从接口返回中提取指定车型车辆列表。"""
    if not isinstance(cars_data, dict):
        return []
    cars_payload = cast(dict[str, Any], cars_data)

    group_obj = cars_payload.get(VEHICLE_MODE)
    if not isinstance(group_obj, dict):
        return []
    group_payload = cast(dict[str, Any], group_obj)

    cars_obj = group_payload.get("cars")
    if not isinstance(cars_obj, list):
        return []

    cars_list = cast(list[Any], cars_obj)
    normalized_cars: list[dict[str, Any]] = []
    for car_obj in cars_list:
        if isinstance(car_obj, dict):
            normalized_cars.append(cast(dict[str, Any], car_obj))
    return normalized_cars

async def probe_api_radius():
    async with SevenMaClient() as client:
        print(f"开始在选区内寻找测试目标车辆（车型模式: {VEHICLE_MODE}）...")
        target_car = None
        
        # 1. 尝试寻找一辆可用车辆
        for _ in range(5):  # 最多尝试5次随机点
            start_lat, start_lon = get_random_start_point()
            print(f"尝试中心点: {start_lat:.6f}, {start_lon:.6f}")
            data = await client.get_new_surrounding_cars(latitude=start_lat, longitude=start_lon)

            mode_cars = get_cars_by_mode(data)
            if mode_cars:
                target_car = mode_cars[0]
                break
            await asyncio.sleep(1) # 避免请求过快
            
        if not target_car:
            print("❌ 在选区内未找到任何可用车辆，请确认该区域是否有车。")
            return

        target_id = int(target_car["id"])
        target_lat = float(target_car["latitude"])
        target_lon = float(target_car["longitude"])
        print(f"✅ 找到目标车辆！ID: {target_id}, 坐标: {target_lat}, {target_lon}")
        print("开始执行二分法探测 API 返回半径...")

        # 2. 二分法探测半径
        low_m = 0.0
        high_m = 200.0  # 设定初始最大探测距离为 200 米
        tolerance = 1.0  # 精度控制在 1 米以内
        bearing = 0.0    # 默认向正北方向移动测试

        max_valid_radius = 0.0

        while (high_m - low_m) > tolerance:
            mid_m = (low_m + high_m) / 2.0
            test_lat, test_lon = get_destination_point(target_lat, target_lon, mid_m, bearing)
            
            print(f"正在测试距离: {mid_m:.2f} 米...")
            # 调用接口时，假装我们站在 test_lat, test_lon 的位置
            test_data = await client.get_new_surrounding_cars(latitude=test_lat, longitude=test_lon)
            
            if check_car_in_response(target_id, test_data):
                # 如果能看到车，说明真实半径 >= mid_m
                max_valid_radius = mid_m
                low_m = mid_m
            else:
                # 如果看不到车，说明真实半径 < mid_m
                high_m = mid_m
                
            await asyncio.sleep(0.5)  # 加上轻微的延迟防止触发 429 限流

        print("-" * 30)
        print(f"🎯 探测完成！API 的车辆搜寻半径约为: {max_valid_radius:.2f} 米")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(probe_api_radius())