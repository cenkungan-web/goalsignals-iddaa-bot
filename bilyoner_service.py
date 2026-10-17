import urllib.request
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.bilyoner.com/iddaa/futbol',
    'Origin': 'https://www.bilyoner.com'
}

BASE_API = "https://www.bilyoner.com/api"

def normalize_text(text: str) -> str:
    """Normalize Turkish characters and lowercases for forgiving searches."""
    if not text:
        return ""
    t = str(text).strip()
    t = t.replace('İ', 'i').replace('I', 'ı').replace('ı', 'i')
    t = t.replace('Ö', 'ö').replace('ö', 'o')
    t = t.replace('Ü', 'ü').replace('ü', 'u')
    t = t.replace('Ş', 'ş').replace('ş', 's')
    t = t.replace('Ç', 'ç').replace('ç', 'c')
    t = t.replace('Ğ', 'ğ').replace('ğ', 'g')
    t = t.lower()
    t = re.sub(r'[\s\-_/:]+', ' ', t).strip()
    return t

class BilyonerService:
    def __init__(self, max_workers: int = 15):
        self.max_workers = max_workers

    def fetch_bulletin_events(self, tab_type: int = 1, bulletin_type: int = 2) -> Dict[str, Any]:
        """
        Fetch bulletin events.
        tab_type: 1=Futbol, 2=Basketbol, 5=Tenis, 23=Voleybol, 9999=Tümü
        bulletin_type: 2=Maç Öncesi, 1=Canlı
        """
        url = f"{BASE_API}/v3/mobile/aggregator/gamelist/all/v1?tabType={tab_type}&bulletinType={bulletin_type}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("events", {})

    def fetch_single_match_card(self, event_id: int, is_live: bool = False) -> Optional[Dict[str, Any]]:
        url = f"{BASE_API}/v3/mobile/aggregator/match-card/{event_id}/odds?isLiveEvent={'true' if is_live else 'false'}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            return None

    def parse_event(self, event_id: int, ev_data: Dict[str, Any], card_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        home_team = (card_data and card_data.get("homeTeam")) or ev_data.get("htn") or "Ev Sahibi"
        away_team = (card_data and card_data.get("awayTeam")) or ev_data.get("atn") or "Deplasman"
        league = ev_data.get("lgn") or ev_data.get("slgn") or "Lig"
        start_date = ev_data.get("strd") or ""
        start_time = ev_data.get("strt") or ""
        mbs = ev_data.get("mbs") or 1
        is_live = bool(ev_data.get("il", 0))

        markets = []
        unique_market_names = set()

        # If card_data is available, parse detailed markets from 'Tümü' tab
        if card_data:
            tabs = card_data.get("oddGroupTabs", [])
            target_tab = None
            for t in tabs:
                if t.get("id") == 1 or "tum" in normalize_text(t.get("title", "")):
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
                        if not o_name or not o_val or str(o_val) in ("0", "None"):
                            continue
                        try:
                            f_val = round(float(str(o_val).replace(',', '.')), 2)
                        except ValueError:
                            continue

                        clean_name = str(o_name).strip()
                        odds_list.append({
                            "name": clean_name,
                            "norm_name": normalize_text(clean_name),
                            "odd": f_val,
                            "odd_str": f"{f_val:.2f}",
                            "mbs": o.get("mbs", m_mbs),
                            "selection_id": o.get("id")
                        })

                    if odds_list:
                        markets.append({
                            "market_name": m_name,
                            "norm_market_name": normalize_text(m_name),
                            "mbs": m_mbs,
                            "odds": odds_list
                        })
                        unique_market_names.add(m_name)

        # Fallback to basic market groups from bulletin if no card parsed
        if not markets and "marketGroups" in ev_data:
            for mg in ev_data.get("marketGroups", []):
                for o in mg.get("odds", []):
                    mrn = o.get("mrn")
                    if not mrn or mrn == "None":
                        continue
                    o_name = o.get("n")
                    o_val = o.get("val")
                    if not o_name or not o_val or str(o_val) in ("0", "None"):
                        continue
                    try:
                        f_val = round(float(str(o_val).replace(',', '.')), 2)
                    except ValueError:
                        continue

                    # Group by market name
                    existing = next((m for m in markets if m["market_name"] == mrn), None)
                    clean_name = str(o_name).strip()
                    odd_item = {
                        "name": clean_name,
                        "norm_name": normalize_text(clean_name),
                        "odd": f_val,
                        "odd_str": f"{f_val:.2f}",
                        "mbs": o.get("mbs", mbs),
                        "selection_id": o.get("id")
                    }
                    if existing:
                        existing["odds"].append(odd_item)
                    else:
                        markets.append({
                            "market_name": mrn,
                            "norm_market_name": normalize_text(mrn),
                            "mbs": mbs,
                            "odds": [odd_item]
                        })
                        unique_market_names.add(mrn)

        return {
            "event_id": event_id,
            "home_team": home_team,
            "away_team": away_team,
            "match_title": f"{home_team} - {away_team}",
            "league": league,
            "start_date": start_date,
            "start_time": start_time,
            "match_time": f"{start_date} {start_time}".strip(),
            "mbs": mbs,
            "is_live": is_live,
            "markets_count": len(markets),
            "markets": markets
        }

    def fetch_all_matches(self,
                          tab_type: int = 1,
                          bulletin_type: int = 2,
                          limit: Optional[int] = None,
                          progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Fetches all matches and their complete odds in parallel.
        """
        raw_events = self.fetch_bulletin_events(tab_type, bulletin_type)
        event_ids = list(raw_events.keys())
        if limit:
            event_ids = event_ids[:limit]

        total = len(event_ids)
        parsed_matches = []
        completed = 0

        is_live = (bulletin_type == 1)

        def worker(eid):
            ev_data = raw_events[eid]
            card = self.fetch_single_match_card(int(eid), is_live=is_live)
            return self.parse_event(int(eid), ev_data, card)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {executor.submit(worker, eid): eid for eid in event_ids}
            for future in as_completed(future_to_id):
                completed += 1
                try:
                    match_data = future.result()
                    parsed_matches.append(match_data)
                    if progress_callback:
                        progress_callback(completed, total, match_data["match_title"])
                except Exception as e:
                    if progress_callback:
                        progress_callback(completed, total, f"Hata ({future_to_id[future]}): {e}")

        # Keep same order as bulletin
        id_order = {int(eid): i for i, eid in enumerate(event_ids)}
        parsed_matches.sort(key=lambda m: id_order.get(m["event_id"], 999999))
        return parsed_matches
