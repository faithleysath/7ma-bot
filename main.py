from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sevenma_sdk import SevenMaClient  # 导入你的 SDK

app = FastAPI()

# 挂载前端静态文件 (把修改后的 geo_fencing.html 放在 static 文件夹下并改名为 index.html)
app.mount("/web", StaticFiles(directory="static", html=True), name="static")

@app.get("/api/cars")
async def get_cars(latitude: float, longitude: float):
    # 使用你的 SDK 去真正请求官方接口
    async with SevenMaClient() as client:
        try:
            # 这里的 client 内部已经帮你把所有伪装的 Header 都带上了
            cars_data = await client.get_new_surrounding_cars(
                latitude=latitude, 
                longitude=longitude
            )
            return cars_data
        except Exception as e:
            return {"error": str(e)}