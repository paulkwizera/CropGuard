import os
import requests
import geocoder
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def detect_current_city() -> str:
    """Detect current city safely with fallback."""
    try:
        # 2s to prevent hangs
        g = geocoder.ip('me', timeout=2)
        if g.ok and g.city:
            return g.city
    except Exception:
        pass
    return None

def get_weather(city_name: str) -> dict:
    """Fetch 5-day weather data from OpenWeatherMap API."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city_name},RW&appid={api_key}&units=metric"
    
    response = requests.get(url, timeout=5)
    if response.status_code != 200:
        raise Exception(f"City '{city_name}' not found: {response.json().get('message')}")
    
    return response.json()

def generate_agricultural_advisory(city: str, weather_data: dict, language: str = "Kinyarwanda") -> str:
    """Pass weather data to Gemini for agricultural recommendations."""
    
    forecast_summary = []
    for item in weather_data['list'][:8]:  # 24-hour window
        forecast_summary.append({
            "datetime": item['dt_txt'],
            "temp_celsius": item['main']['temp'],
            "humidity": item['main']['humidity'],
            "weather": item['weather'][0]['description'],
            "wind_speed_m_s": item['wind']['speed'],
            "rain_mm": item.get('rain', {}).get('3h', 0)
        })

    prompt = f"""
    You are an expert agricultural advisor assisting smallholder farmers in Rwanda.
    
    Location: {city}, Rwanda
    Upcoming Weather Data (Next 24 Hours): {forecast_summary}
    
    Instructions:
    1. Summarize the weather forecast simply.
    2. Provide clear, direct agricultural recommendations for farmers in {city} (e.g., whether to spray pesticides, irrigate crops, harvest early, or protect soil against erosion).
    3. Output the entire response in **{language}** (or English if requested). Keep the tone encouraging, practical, and clear.
    """
    response_stream = client.models.generate_content_stream(
        model="gemini-3.6-flash",
        contents=prompt
    )
    full_text = ""
    for chunk in response_stream:
        print(chunk.text, end="", flush=True)
        full_text += chunk.text

    print()
    return full_text 

if __name__ == "__main__":
    print("=== RWANDA FARMER WEATHER ADVISORY ===")
    print("1. Auto-detect my location")
    print("2. Enter city/district manually")
    
    choice = input("Select an option (1 or 2): ").strip()
    target_city = None

    if choice == "1":
        print("Detecting your location...")
        target_city = detect_current_city()
        if target_city:
            print(f"Auto-detected location: {target_city}")
        else:
            print("Could not auto-detect location. Switching to manual input.")
            target_city = input("Enter your city/district in Rwanda (e.g., Musanze, Huye, Kigali): ").strip()
    else:
        target_city = input("Enter your city/district in Rwanda (e.g., Musanze, Huye, Kigali): ").strip()

    if target_city:
        try:
            print(f"\nFetching weather for {target_city}...")
            raw_weather = get_weather(target_city)
            
            print("Generating agricultural advisory via Gemini...\n")
            advisory = generate_agricultural_advisory(target_city, raw_weather, language="Kinyarwanda")
            
            print(f"=== AGRICULTURAL ADVISORY ({target_city.upper()}) ===")
            print(advisory)
            
        except Exception as e:
            print(f"Error: {e}")