import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import requests
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# .env에서 토큰 로드
load_dotenv()
weather_token = os.getenv("weather_token")
weather_api = os.getenv("weathers_api")

llm = ChatOpenAI(
    temperature=0.5,  # 창의성 (0.0 ~ 2.0)
    model_name="gpt-4.1-nano",  # 모델명
)
template = [
    (
        "system",
        "당신은 당신은 여행 및 라이프스타일 전문가입니다. 당신의 이름은 국멘_오늘은 뭐해요? 입니다. 날씨와 지역 정보를 바탕으로 활동을 추천해 주세요",
    ),
    ("human", "{prompt}"),
]
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix="/", intents=intents)
weather_cache = {}


@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user.name}")


@bot.command(name="날씨")
async def add_birth(ctx, region: str):
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={region}&limit=1&appid={weather_api}"
    response = requests.get(geo_url).json()
    lat = response[0]["lat"]
    lon = response[0]["lon"]

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api}&units=metric&lang=kr"
    response_w = requests.get(weather_url).json()
    temp = response_w["main"]["temp"]
    feel_temp = response_w["main"]["feels_like"]
    humid = response_w["main"]["humidity"]
    rain = response_w.get("rain", {}).get("1h", 0)
    wind_speed = response_w["wind"]["speed"]
    if rain == 0:
        rain_say = "🌧️지금은 비가 안오네요~"
    else:
        rain_say = f"🌧️지금은 비가 {rain}mm 오고 있어요~"
    await ctx.send(
        f"🌤️{region}의 현재 날씨 정보입니다:\n\n"
        f"🌡️온도: {temp}°C\n\n"
        f"🤒체감 온도: {feel_temp}°C\n\n"
        f"💧습도: {humid}%\n\n"
        f"{rain_say}\n\n"
        f"🌬️풍속: {wind_speed}m/s\n\n"
    )
    weather_cache[ctx.author.id] = {
        "region": region,
        "temp": temp,
        "feel_temp": feel_temp,
        "humid": humid,
        "rain": rain,
        "wind_speed": wind_speed,
        "description": response_w["weather"][0]["description"],
    }


@bot.command(name="추천")
async def recommend_activity(ctx):
    data = weather_cache.get(ctx.author.id)
    if not data:
        await ctx.send("⚠️ 먼저 `/날씨 지역명` 으로 날씨 정보를 확인해주세요!")
        return

    # LLM 프롬프트 생성
    prompts = (
        f"현재 위치는 {data['region']}이고, 온도는 {data['temp']}도입니다. "
        f"체감 온도는 {data['feel_temp']}도이며, 날씨는 '{data['description']}'이고 "
        f"습도는 {data['humid']}%, 바람은 {data['wind_speed']}m/s입니다. "
        f"{'비가 오고 있습니다.' if data['rain'] > 0 else '비는 오지 않습니다.'} "
        f"{data['region']} 지역의 특색 있는 장소나 활동을 포함하여, "
        f"이런 날씨에 적절한 하루 활동을 한국어로 추천해 주세요."
    )
    prompt = ChatPromptTemplate.from_messages(template)
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"prompt": prompts})
    MAX_LENGTH = 1500
    for i in range(0, len(result), MAX_LENGTH):
        chunk = result[i : i + MAX_LENGTH]
        await ctx.send(f"{ctx.author.mention}{chunk}")


bot.run(weather_token)
