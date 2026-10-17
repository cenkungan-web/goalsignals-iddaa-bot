import threading
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from bilyoner_service import BilyonerService, normalize_text

class CacheEngine:
    def __init__(self, service: Optional[BilyonerService] = None, auto_refresh_interval: int = 900):
        self.service = service or BilyonerService(max_workers=15)
        self.matches: List[Dict[str, Any]] = []
        self.last_updated: Optional[datetime] = None
        self.is_scanning: bool = False
        self.scan_progress = {"current": 0, "total": 0, "status": "Boşta", "percent": 0}
        self.markets_catalog: Dict[str, List[str]] = {}
        self.auto_refresh_interval = auto_refresh_interval  # Default 15 mins (900s)
        self._lock = threading.Lock()
        self._auto_refresh_thread: Optional[threading.Thread] = None
        self._stop_auto_refresh = False

    def start_auto_refresh_daemon(self):
        """Starts 24/7 background scheduler for cloud/server deployment."""
        if self._auto_refresh_thread and self._auto_refresh_thread.is_alive():
            return
        self._stop_auto_refresh = False
        self._auto_refresh_thread = threading.Thread(target=self._auto_refresh_worker, daemon=True)
        self._auto_refresh_thread.start()

    def _auto_refresh_worker(self):
        while not self._stop_auto_refresh:
            time.sleep(self.auto_refresh_interval)
            if not self.is_scanning:
                print(f"[AutoRefresh] 24/7 otomatik bülten taraması başlatılıyor: {datetime.now()}")
                self.start_background_scan(tab_type=1, bulletin_type=2)

    def start_background_scan(self, tab_type: int = 1, bulletin_type: int = 2, limit: Optional[int] = None):
        """Starts asynchronous background scan to refresh the cache."""
        with self._lock:
            if self.is_scanning:
                return False
            self.is_scanning = True
            self.scan_progress = {"current": 0, "total": 0, "status": "Bülten alınıyor...", "percent": 0}

        thread = threading.Thread(
            target=self._run_scan,
            args=(tab_type, bulletin_type, limit),
            daemon=True
        )
        thread.start()
        return True

    def _run_scan(self, tab_type: int, bulletin_type: int, limit: Optional[int]):
        def progress_cb(current, total, match_title):
            percent = int((current / total * 100)) if total > 0 else 0
            with self._lock:
                self.scan_progress = {
                    "current": current,
                    "total": total,
                    "status": f"Taranıyor ({current}/{total}): {match_title}",
                    "percent": percent
                }

        try:
            matches = self.service.fetch_all_matches(
                tab_type=tab_type,
                bulletin_type=bulletin_type,
                limit=limit,
                progress_callback=progress_cb
            )
            with self._lock:
                self.matches = matches
                self.last_updated = datetime.now()
                self._build_catalog()
                self.scan_progress = {
                    "current": len(matches),
                    "total": len(matches),
                    "status": f"Tarama tamamlandı! {len(matches)} maç önbelleğe alındı.",
                    "percent": 100
                }
        except Exception as e:
            with self._lock:
                self.scan_progress = {
                    "current": 0,
                    "total": 0,
                    "status": f"Tarama hatası: {str(e)}",
                    "percent": 0
                }
        finally:
            with self._lock:
                self.is_scanning = False

    def _build_catalog(self):
        """Build catalog of distinct market names and their available selections."""
        catalog: Dict[str, Set[str]] = {}
        for m in self.matches:
            for market in m.get("markets", []):
                m_name = market["market_name"]
                if m_name not in catalog:
                    catalog[m_name] = set()
                for o in market.get("odds", []):
                    catalog[m_name].add(o["name"])

        self.markets_catalog = {
            m_name: sorted(list(options))
            for m_name, options in sorted(catalog.items())
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_scanning": self.is_scanning,
                "matches_count": len(self.matches),
                "last_updated": self.last_updated.strftime("%d.%m.%Y %H:%M:%S") if self.last_updated else None,
                "progress": self.scan_progress,
                "markets_count": len(self.markets_catalog),
                "auto_refresh_interval_sec": self.auto_refresh_interval
            }

    def get_catalog(self) -> Dict[str, List[str]]:
        with self._lock:
            return self.markets_catalog

    def _check_single_criterion(self, match: Dict[str, Any], crit: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns list of matching odds in this match for a single criterion."""
        norm_market = normalize_text(crit.get("market") or "")
        norm_selection = normalize_text(crit.get("selection") or "")
        target_odd = crit.get("target_odd")
        tolerance = float(crit.get("tolerance") or 0.0)
        min_odd = crit.get("min_odd")
        max_odd = crit.get("max_odd")

        def matches_selection(item_norm_name: str, target_norm: str) -> bool:
            if not target_norm:
                return True
            if item_norm_name == target_norm:
                return True
            clean_item = re.sub(r'[^0-9]', '', item_norm_name)
            clean_target = re.sub(r'[^0-9]', '', target_norm)
            if clean_item and clean_target and clean_item == clean_target:
                return True
            return target_norm in item_norm_name

        def matches_market(item_norm_market: str, target_norm: str) -> bool:
            if not target_norm:
                return True
            if "iy skor" in target_norm:
                target_norm = target_norm.replace("iy skor", "ilk yari skor")
            if "ms" in target_norm and len(target_norm) <= 4:
                target_norm = target_norm.replace("ms", "mac sonucu")
            if "kg" in target_norm:
                target_norm = target_norm.replace("kg", "karsilikli gol")

            words = target_norm.split()
            return all(w in item_norm_market for w in words)

        matched_odds = []
        for market in match.get("markets", []):
            m_name = market["market_name"]
            norm_m_name = market["norm_market_name"]

            if not matches_market(norm_m_name, norm_market):
                continue

            for odd_item in market.get("odds", []):
                o_name = odd_item["name"]
                norm_o_name = odd_item["norm_name"]
                odd_val = odd_item["odd"]

                if not matches_selection(norm_o_name, norm_selection):
                    continue

                if target_odd is not None:
                    t_min = round(target_odd - tolerance, 2)
                    t_max = round(target_odd + tolerance, 2)
                    if not (t_min <= odd_val <= t_max):
                        continue

                if min_odd is not None and odd_val < min_odd:
                    continue
                if max_odd is not None and odd_val > max_odd:
                    continue

                matched_odds.append({
                    "market_name": m_name,
                    "selection": o_name,
                    "odd": odd_val,
                    "odd_str": odd_item["odd_str"],
                    "mbs": odd_item.get("mbs", match["mbs"])
                })

        return matched_odds

    def search_multi(self,
                     criteria: List[Dict[str, Any]],
                     match_mode: str = "AND",
                     league_query: Optional[str] = None,
                     match_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Multi-criteria search engine.
        match_mode:
          - 'AND': The match MUST satisfy ALL criteria (e.g. both IY 0-0=2.20 AND MS 1=1.80 in same match).
          - 'OR': The match satisfies AT LEAST ONE criterion.
        """
        with self._lock:
            matches_snapshot = list(self.matches)

        norm_league = normalize_text(league_query) if league_query else ""
        norm_match = normalize_text(match_text) if match_text else ""
        match_mode_upper = match_mode.upper().strip()

        # Filter out empty criteria
        active_criteria = [
            c for c in criteria
            if c.get("market") or c.get("selection") or c.get("target_odd") is not None or c.get("min_odd") is not None
        ]
        if not active_criteria:
            active_criteria = [{}]

        results = []

        for match in matches_snapshot:
            # Check league filter
            if norm_league and norm_league not in normalize_text(match.get("league", "")):
                continue

            # Check match text (team name)
            if norm_match and norm_match not in normalize_text(match.get("match_title", "")):
                continue

            criteria_matches: List[List[Dict[str, Any]]] = []
            for crit in active_criteria:
                matched_items = self._check_single_criterion(match, crit)
                criteria_matches.append(matched_items)

            if match_mode_upper == "AND":
                # Every criterion must have at least 1 matching odd in this match
                if all(len(items) > 0 for items in criteria_matches):
                    # Flatten matched odds from all criteria
                    all_matched_odds = []
                    for items in criteria_matches:
                        for itm in items:
                            if itm not in all_matched_odds:
                                all_matched_odds.append(itm)

                    results.append({
                        "event_id": match["event_id"],
                        "match_title": match["match_title"],
                        "home_team": match["home_team"],
                        "away_team": match["away_team"],
                        "league": match["league"],
                        "match_time": match["match_time"],
                        "is_live": match["is_live"],
                        "matched_odds": all_matched_odds,
                        # For single-criterion display compatibility:
                        "market_name": all_matched_odds[0]["market_name"],
                        "selection": all_matched_odds[0]["selection"],
                        "odd": all_matched_odds[0]["odd"],
                        "odd_str": all_matched_odds[0]["odd_str"],
                        "mbs": all_matched_odds[0]["mbs"]
                    })
            else:  # OR mode
                if any(len(items) > 0 for items in criteria_matches):
                    all_matched_odds = []
                    for items in criteria_matches:
                        for itm in items:
                            if itm not in all_matched_odds:
                                all_matched_odds.append(itm)

                    results.append({
                        "event_id": match["event_id"],
                        "match_title": match["match_title"],
                        "home_team": match["home_team"],
                        "away_team": match["away_team"],
                        "league": match["league"],
                        "match_time": match["match_time"],
                        "is_live": match["is_live"],
                        "matched_odds": all_matched_odds,
                        "market_name": all_matched_odds[0]["market_name"],
                        "selection": all_matched_odds[0]["selection"],
                        "odd": all_matched_odds[0]["odd"],
                        "odd_str": all_matched_odds[0]["odd_str"],
                        "mbs": all_matched_odds[0]["mbs"]
                    })

        return results

    def search(self, **kwargs) -> List[Dict[str, Any]]:
        """Backwards compatible single-criterion search."""
        crit = {
            "market": kwargs.get("market_query"),
            "selection": kwargs.get("selection_query"),
            "target_odd": kwargs.get("target_odd"),
            "tolerance": kwargs.get("tolerance", 0.0),
            "min_odd": kwargs.get("min_odd"),
            "max_odd": kwargs.get("max_odd"),
        }
        return self.search_multi(
            criteria=[crit],
            match_mode="AND",
            league_query=kwargs.get("league_query"),
            match_text=kwargs.get("match_text")
        )
