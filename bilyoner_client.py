import asyncio
import httpx
import re
from typing import List, Dict, Any, Optional

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.bilyoner.com',
    'Referer': 'https://www.bilyoner.com/iddaa/futbol'
}

BASE_API = "https://www.bilyoner.com/api"

def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = t.replace('İ', 'i').replace('I', 'ı').replace('ı', 'i')
    t = t.replace('Ö', 'ö').replace('ö', 'o')
    t = t.replace('Ü', 'ü').replace('ü', 'u')
    t = t.replace('Ş', 'ş').replace('ş', 's')
    t = t.replace('Ç', 'ç').replace('ç', 'c')
    t = t.replace('Ğ', 'ğ').replace('ğ', 'g')
    t = t.lower()
    t = re.sub(r'\s+', ' ', t)
    return t

class BilyonerClient:
    def __init__(self):
        limits = httpx.Limits(max_keepalive_connections=30, max_connections=50)
        timeout = httpx.Timeout(10.0, connect=5.0)
        self.client = httpx.AsyncClient(headers=HEADERS, limits=limits, timeout=timeout)

    async def close(self):
        await self.client.aclose()

    async def get_bulletin_events(self, tab_type: int = 1, bulletin_type: int = 2) -> Dict[str, Any]:
        """
        tab_type: 1=Futbol, 2=Basketbol, 5=Tenis, 23=Voleybol, 9999=Tümü
        bulletin_type: 2=Maç Öncesi (Prematch), 1=Canlı (Live)
        """
        url = f"{BASE_API}/v3/mobile/aggregator/gamelist/all/v1?tabType={tab_type}&bulletinType={bulletin_type}"
        resp = await self.client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("events", {})

    async def get_match_odds(self, event_id: int, is_live: bool = False) -> Optional[Dict[str, Any]]:
        url = f"{BASE_API}/v3/mobile/aggregator/match-card/{event_id}/odds?isLiveEvent={'true' if is_live else 'false'}"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            return None
        return None

    def parse_match_details(self, event_id: int, raw_bulletin_ev: Dict[str, Any], raw_card: Dict[str, Any]) -> Dict[str, Any]:
        home_team = raw_card.get("homeTeam") or raw_bulletin_ev.get("htn") or "Ev Sahibi"
        away_team = raw_card.get("awayTeam") or raw_bulletin_ev.get("atn") or "Deplasman"
        league = raw_bulletin_ev.get("lgn") or raw_bulletin_ev.get("slgn") or "Lig"
        start_date = raw_bulletin_ev.get("strd") or ""
        start_time = raw_bulletin_ev.get("strt") or ""
        mbs = raw_bulletin_ev.get("mbs") or 1
        is_live = bool(raw_bulletin_ev.get("il", 0))

        tabs = raw_card.get("oddGroupTabs", [])
        markets_parsed = []

        # Find "Tümü" tab (usually id: 1) or take first tab
        target_tab = None
        for t in tabs:
            if t.get("id") == 1 or "tüm" in normalize_text(t.get("title", "")):
                target_tab = t
                break
        if not target_tab and len(tabs) > 0:
            target_tab = tabs[0]

        if target_tab:
            for m in target_tab.get("matchCardOdds", []):
                m_name = m.get("name") or m.get("shortName") or ""
                m_mbs = m.get("mbs", mbs)
                odds_list = []
                for o in m.get("oddList", []):
                    o_name = o.get("n")
                    o_val = o.get("val")
                    if not o_name or not o_val or o_val == "0":
                        continue
                    try:
                        f_val = float(str(o_val).replace(',', '.'))
                    except ValueError:
                        continue

                    odds_list.append({
                        "name": str(o_name).strip(),
                        "odd_str": str(o_val).strip(),
                        "odd": f_val,
                        "selection_id": o.get("id"),
                        "mbs": o.get("mbs", m_mbs)
                    })

                if odds_list:
                    markets_parsed.append({
                        "market_name": m_name,
                        "normalized_name": normalize_text(m_name),
                        "odds": odds_list
                    })

        return {
            "event_id": event_id,
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "start_date": start_date,
            "start_time": start_time,
            "match_time": f"{start_date} {start_time}".strip(),
            "mbs": mbs,
            "is_live": is_live,
            "bilyoner_url": f"https://www.bilyoner.com/iddaa/futbol/{event_id}",
            "markets": markets_parsed
        }
