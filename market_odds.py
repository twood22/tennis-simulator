"""Read-only prediction-market snapshots for ATP match winners.

The module deliberately uses only public, unauthenticated endpoints. A market
lookup is advisory: provider failures are returned as data and never prevent a
simulation from completing.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen


KALSHI_API = "https://external-api.kalshi.com/trade-api/v2"
POLYMARKET_API = "https://gamma-api.polymarket.com"
REQUEST_TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).strip().replace(" ", "T")
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_utc(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fetch_json(url):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "tennis-simulator/1.0",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Provider response was too large")
        return json.loads(body)


def _tokens(name):
    normalized = unicodedata.normalize("NFKD", str(name))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return tuple(re.findall(r"[a-z0-9]+", ascii_name))


def _names_match(requested, offered):
    """Match full names while allowing a provider to include extra surnames."""
    requested_tokens = _tokens(requested)
    offered_tokens = _tokens(offered)
    if not requested_tokens or not offered_tokens:
        return False
    if requested_tokens == offered_tokens:
        return True

    requested_set = set(requested_tokens)
    offered_set = set(offered_tokens)
    if len(requested_tokens) >= 2 and requested_set.issubset(offered_set):
        return requested_tokens[0] == offered_tokens[0]
    if len(offered_tokens) >= 2 and offered_set.issubset(requested_set):
        return requested_tokens[0] == offered_tokens[0]
    return False


def _map_players(player1, player2, offered_names):
    if len(offered_names) != 2:
        return None
    direct = (
        _names_match(player1, offered_names[0])
        and _names_match(player2, offered_names[1])
    )
    reverse = (
        _names_match(player1, offered_names[1])
        and _names_match(player2, offered_names[0])
    )
    if direct == reverse:
        return None
    return (0, 1) if direct else (1, 0)


def resolve_player_name(offered_name, known_names):
    """Resolve a provider label to one unambiguous simulator player name."""
    matches = [name for name in known_names if _names_match(name, offered_name)]
    return matches[0] if len(matches) == 1 else None


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _probability(value):
    value = _number(value)
    if value is None or not 0 <= value <= 1:
        return None
    return value


def _json_list(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


def _normalize_pair(first, second):
    if first is None or second is None:
        return None
    total = first + second
    if total <= 0:
        return None
    return first / total, second / total, total


def _unavailable(provider, reason, status="unavailable"):
    return {
        "provider": provider,
        "status": status,
        "reason": reason,
        "fetched_at": _utc_now(),
    }


def _kalshi_midpoint(market):
    bid = _probability(market.get("yes_bid_dollars"))
    ask = _probability(market.get("yes_ask_dollars"))
    if bid is not None and ask is not None and bid <= ask:
        return (bid + ask) / 2, bid, ask
    last = _probability(market.get("last_price_dollars"))
    return (last, bid, ask) if last is not None else (None, bid, ask)


def fetch_kalshi_odds(player1, player2, fetcher=_fetch_json):
    params = urlencode({
        "series_ticker": "KXATPMATCH",
        "status": "open",
        "limit": 1000,
    })
    source_url = f"{KALSHI_API}/markets?{params}"
    try:
        payload = fetcher(source_url)
        markets = payload.get("markets", [])
        if not isinstance(markets, list):
            raise ValueError("Unexpected market response")

        events = {}
        for market in markets:
            if isinstance(market, dict) and market.get("event_ticker"):
                events.setdefault(market["event_ticker"], []).append(market)

        candidates = []
        for event_ticker, event_markets in events.items():
            player1_markets = [
                market for market in event_markets
                if _names_match(player1, market.get("yes_sub_title", ""))
            ]
            player2_markets = [
                market for market in event_markets
                if _names_match(player2, market.get("yes_sub_title", ""))
            ]
            if not player1_markets or not player2_markets:
                continue

            for first_market in player1_markets:
                for second_market in player2_markets:
                    if first_market.get("ticker") == second_market.get("ticker"):
                        continue
                    first_price, first_bid, first_ask = _kalshi_midpoint(first_market)
                    second_price, second_bid, second_ask = _kalshi_midpoint(second_market)
                    normalized = _normalize_pair(first_price, second_price)
                    if normalized is None:
                        continue
                    first_probability, second_probability, raw_sum = normalized
                    volumes = [
                        value for value in (
                            _number(first_market.get("volume_fp")),
                            _number(second_market.get("volume_fp")),
                        )
                        if value is not None
                    ]
                    candidates.append({
                        "provider": "kalshi",
                        "status": "available",
                        "market_title": first_market.get("title") or second_market.get("title"),
                        "event_ticker": event_ticker,
                        "source_url": f"{KALSHI_API}/events/{event_ticker}",
                        "pricing_method": "normalized midpoint of each player's YES bid and ask",
                        "raw_probability_sum": round(raw_sum, 6),
                        "player1": {
                            "name": player1,
                            "market_label": first_market.get("yes_sub_title"),
                            "probability": round(first_probability, 6),
                            "bid": first_bid,
                            "ask": first_ask,
                        },
                        "player2": {
                            "name": player2,
                            "market_label": second_market.get("yes_sub_title"),
                            "probability": round(second_probability, 6),
                            "bid": second_bid,
                            "ask": second_ask,
                        },
                        "volume": round(sum(volumes), 4) if volumes else None,
                        "volume_note": "sum of the two player YES-market volumes",
                        "provider_updated_at": max(
                            filter(None, (
                                first_market.get("updated_time"),
                                second_market.get("updated_time"),
                            )),
                            default=None,
                        ),
                        "fetched_at": _utc_now(),
                    })

        if not candidates:
            return _unavailable("kalshi", "No exact open ATP match market found")
        return max(candidates, key=lambda item: item.get("volume") or 0)
    except Exception:
        return _unavailable("kalshi", "Kalshi market data is temporarily unavailable", "error")


def fetch_polymarket_odds(player1, player2, fetcher=_fetch_json):
    params = urlencode({"q": f"{player1} {player2}", "limit_per_type": 20})
    source_url = f"{POLYMARKET_API}/public-search?{params}"
    try:
        payload = fetcher(source_url)
        events = payload.get("events", [])
        if not isinstance(events, list):
            raise ValueError("Unexpected search response")

        candidates = []
        for event in events:
            if not isinstance(event, dict) or not event.get("active") or event.get("closed"):
                continue
            for market in event.get("markets", []):
                if (
                    not isinstance(market, dict)
                    or not market.get("active")
                    or market.get("closed")
                    or market.get("sportsMarketType") != "moneyline"
                ):
                    continue
                outcomes = _json_list(market.get("outcomes"))
                prices = _json_list(market.get("outcomePrices"))
                if outcomes is None or prices is None or len(prices) != 2:
                    continue
                mapping = _map_players(player1, player2, outcomes)
                if mapping is None:
                    continue
                parsed_prices = [_probability(price) for price in prices]
                if None in parsed_prices:
                    continue
                normalized = _normalize_pair(
                    parsed_prices[mapping[0]], parsed_prices[mapping[1]]
                )
                if normalized is None:
                    continue
                first_probability, second_probability, raw_sum = normalized
                slug = event.get("slug")
                candidates.append({
                    "provider": "polymarket",
                    "status": "available",
                    "market_title": market.get("question") or event.get("title"),
                    "market_id": market.get("id"),
                    "source_url": (
                        f"https://polymarket.com/event/{slug}" if slug else source_url
                    ),
                    "pricing_method": "normalized published outcome prices",
                    "raw_probability_sum": round(raw_sum, 6),
                    "player1": {
                        "name": player1,
                        "market_label": outcomes[mapping[0]],
                        "probability": round(first_probability, 6),
                    },
                    "player2": {
                        "name": player2,
                        "market_label": outcomes[mapping[1]],
                        "probability": round(second_probability, 6),
                    },
                    "volume": _number(market.get("volume")),
                    "liquidity": _number(market.get("liquidity")),
                    "provider_updated_at": market.get("updatedAt") or event.get("updatedAt"),
                    "fetched_at": _utc_now(),
                })

        if not candidates:
            return _unavailable("polymarket", "No exact active match-winner market found")
        return max(candidates, key=lambda item: item.get("volume") or 0)
    except Exception:
        return _unavailable(
            "polymarket", "Polymarket data is temporarily unavailable", "error"
        )


def build_market_comparison(player1, player2, providers, model_probabilities=None):
    """Build a transparent consensus from already-fetched provider snapshots."""
    available = [item for item in providers if item["status"] == "available"]
    response = {
        "status": (
            "available" if len(available) == 2
            else "partial" if available
            else "unavailable"
        ),
        "providers": providers,
        "fetched_at": _utc_now(),
        "notice": (
            "Live public-market snapshot; prices may be delayed, illiquid, or unavailable. "
            "This is a comparison tool, not betting advice."
        ),
    }
    if not available:
        return response

    first_consensus = sum(
        item["player1"]["probability"] for item in available
    ) / len(available)
    second_consensus = sum(
        item["player2"]["probability"] for item in available
    ) / len(available)
    normalized = _normalize_pair(first_consensus, second_consensus)
    first_consensus, second_consensus, _ = normalized
    response["consensus"] = {
        "method": "unweighted mean of available provider probabilities",
        "provider_count": len(available),
        "player1": {"name": player1, "probability": round(first_consensus, 6)},
        "player2": {"name": player2, "probability": round(second_consensus, 6)},
    }

    if model_probabilities:
        comparisons = {}
        for surface, probability in model_probabilities.items():
            parsed = _probability(probability)
            if parsed is None:
                continue
            comparisons[surface] = {
                "player1_model_probability": round(parsed, 6),
                "player1_model_minus_market_pp": round(
                    (parsed - first_consensus) * 100, 2
                ),
                "player2_model_probability": round(1 - parsed, 6),
                "player2_model_minus_market_pp": round(
                    ((1 - parsed) - second_consensus) * 100, 2
                ),
            }
        response["model_comparison"] = comparisons
    return response


def get_market_comparison(player1, player2, model_probabilities=None,
                          fetcher=_fetch_json):
    """Fetch both providers concurrently and compare them with model outputs."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        kalshi_future = executor.submit(fetch_kalshi_odds, player1, player2, fetcher)
        polymarket_future = executor.submit(
            fetch_polymarket_odds, player1, player2, fetcher
        )
        providers = [kalshi_future.result(), polymarket_future.result()]
    return build_market_comparison(
        player1, player2, providers, model_probabilities=model_probabilities
    )


def _provider_snapshot(provider, player1, player2, first_probability,
                       second_probability, **details):
    normalized = _normalize_pair(first_probability, second_probability)
    if normalized is None:
        return None
    first_probability, second_probability, raw_sum = normalized
    return {
        "provider": provider,
        "status": "available",
        "player1": {"name": player1, "probability": round(first_probability, 6)},
        "player2": {"name": player2, "probability": round(second_probability, 6)},
        "raw_probability_sum": round(raw_sum, 6),
        "fetched_at": _utc_now(),
        **details,
    }


def _discover_kalshi_matches(payload, start, end):
    markets = payload.get("markets", []) if isinstance(payload, dict) else []
    grouped = {}
    for market in markets:
        if isinstance(market, dict) and market.get("event_ticker"):
            grouped.setdefault(market["event_ticker"], []).append(market)

    matches = []
    for event_ticker, event_markets in grouped.items():
        priced = []
        for market in event_markets:
            label = str(market.get("yes_sub_title") or "").strip()
            midpoint, bid, ask = _kalshi_midpoint(market)
            if label and midpoint is not None:
                priced.append((market, label, midpoint, bid, ask))
        if len(priced) != 2:
            continue
        first, second = priced
        start_time = _parse_datetime(
            first[0].get("occurrence_datetime")
            or first[0].get("expected_expiration_time")
        )
        if start_time is None or not start <= start_time <= end:
            continue
        snapshot = _provider_snapshot(
            "kalshi",
            first[1],
            second[1],
            first[2],
            second[2],
            market_title=first[0].get("title"),
            event_ticker=event_ticker,
            source_url=f"{KALSHI_API}/events/{event_ticker}",
            pricing_method="normalized midpoint of each player's YES bid and ask",
            provider_updated_at=max(
                filter(None, (
                    first[0].get("updated_time"), second[0].get("updated_time")
                )),
                default=None,
            ),
            volume=round(sum(filter(lambda value: value is not None, (
                _number(first[0].get("volume_fp")),
                _number(second[0].get("volume_fp")),
            ))), 4),
        )
        if snapshot:
            snapshot["player1"].update({"bid": first[3], "ask": first[4]})
            snapshot["player2"].update({"bid": second[3], "ask": second[4]})
            matches.append({
                "player1": first[1],
                "player2": second[1],
                "start_time": _iso_utc(start_time),
                "tournament": None,
                "round": None,
                "provider": snapshot,
            })
    return matches


def _discover_polymarket_matches(payload, start, end):
    events = payload.get("events", []) if isinstance(payload, dict) else []
    matches = []
    for event in events:
        if not isinstance(event, dict) or event.get("closed") or not event.get("active"):
            continue
        for market in event.get("markets") or []:
            if (
                not isinstance(market, dict)
                or market.get("sportsMarketType") != "moneyline"
                or market.get("closed")
                or not market.get("active")
            ):
                continue
            outcomes = _json_list(market.get("outcomes"))
            prices = _json_list(market.get("outcomePrices"))
            if not outcomes or len(outcomes) != 2 or not prices or len(prices) != 2:
                continue
            parsed_prices = [_probability(value) for value in prices]
            if None in parsed_prices:
                continue
            start_time = _parse_datetime(
                market.get("gameStartTime")
                or event.get("startTime")
                or event.get("eventDate")
            )
            if start_time is None or not start <= start_time <= end:
                continue
            title = market.get("question") or event.get("title") or ""
            tournament = title.split(":", 1)[0].strip() if ":" in title else None
            snapshot = _provider_snapshot(
                "polymarket",
                str(outcomes[0]).strip(),
                str(outcomes[1]).strip(),
                parsed_prices[0],
                parsed_prices[1],
                market_title=title,
                market_id=market.get("id"),
                source_url=(
                    f"https://polymarket.com/event/{event['slug']}"
                    if event.get("slug") else f"{POLYMARKET_API}/events/{event.get('id')}"
                ),
                pricing_method="normalized published outcome prices",
                provider_updated_at=market.get("updatedAt") or event.get("updatedAt"),
                volume=_number(market.get("volume")),
                liquidity=_number(market.get("liquidity")),
            )
            if snapshot:
                matches.append({
                    "player1": str(outcomes[0]).strip(),
                    "player2": str(outcomes[1]).strip(),
                    "start_time": _iso_utc(start_time),
                    "tournament": tournament,
                    "round": None,
                    "provider": snapshot,
                })
    return matches


def _canonical_pair_key(player1, player2):
    return tuple(sorted((" ".join(_tokens(player1)), " ".join(_tokens(player2)))))


def _match_identifier(player1, player2, start_time):
    date_part = str(start_time)[:10]
    material = "|".join((*_canonical_pair_key(player1, player2), date_part))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def discover_upcoming_matches(known_names, days=7, now=None, fetcher=_fetch_json):
    """Discover upcoming ATP moneylines with two bounded provider requests."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    start = now_utc - timedelta(minutes=30)
    end = now_utc + timedelta(days=max(1, min(int(days), 7)))

    kalshi_url = (
        f"{KALSHI_API}/markets?"
        + urlencode({"series_ticker": "KXATPMATCH", "status": "open", "limit": 1000})
    )
    polymarket_url = (
        f"{POLYMARKET_API}/events/keyset?"
        + urlencode({
            "series_id": 10365,
            "closed": "false",
            "start_time_min": _iso_utc(start),
            "start_time_max": _iso_utc(end),
            "order": "startTime",
            "ascending": "true",
            "limit": 200,
        })
    )

    errors = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            "kalshi": executor.submit(fetcher, kalshi_url),
            "polymarket": executor.submit(fetcher, polymarket_url),
        }
        payloads = {}
        for provider, future in futures.items():
            try:
                payloads[provider] = future.result()
            except Exception:
                payloads[provider] = {}
                errors.append(f"{provider} discovery is temporarily unavailable")

    discovered = (
        _discover_kalshi_matches(payloads["kalshi"], start, end)
        + _discover_polymarket_matches(payloads["polymarket"], start, end)
    )
    merged = {}
    known_names = tuple(known_names)
    for item in discovered:
        resolved1 = resolve_player_name(item["player1"], known_names)
        resolved2 = resolve_player_name(item["player2"], known_names)
        player1 = resolved1 or item["player1"]
        player2 = resolved2 or item["player2"]
        key = (*_canonical_pair_key(player1, player2), item["start_time"][:10])
        existing = merged.get(key)
        if existing is None:
            existing = {
                "id": _match_identifier(player1, player2, item["start_time"]),
                "player1": player1,
                "player2": player2,
                "player1_in_model": resolved1 is not None,
                "player2_in_model": resolved2 is not None,
                "start_time": item["start_time"],
                "tournament": item.get("tournament"),
                "round": item.get("round"),
                "providers": [],
            }
            merged[key] = existing

        provider = item["provider"]
        mapping = _map_players(existing["player1"], existing["player2"], (
            provider["player1"]["name"], provider["player2"]["name"]
        ))
        if mapping == (1, 0):
            provider = {**provider,
                "player1": {**provider["player2"], "name": existing["player1"]},
                "player2": {**provider["player1"], "name": existing["player2"]},
            }
        elif mapping == (0, 1):
            provider = {**provider,
                "player1": {**provider["player1"], "name": existing["player1"]},
                "player2": {**provider["player2"], "name": existing["player2"]},
            }
        else:
            continue
        existing["providers"] = [
            current for current in existing["providers"]
            if current["provider"] != provider["provider"]
        ]
        existing["providers"].append(provider)
        if item.get("tournament"):
            existing["tournament"] = item["tournament"]
        if item["provider"]["provider"] == "polymarket":
            existing["start_time"] = item["start_time"]

    results = []
    for match in merged.values():
        comparison = build_market_comparison(
            match["player1"], match["player2"], match.pop("providers")
        )
        match["market_comparison"] = comparison
        results.append(match)
    results.sort(key=lambda item: (item["start_time"], item["player1"]))
    return {
        "matches": results,
        "errors": errors,
        "generated_at": _utc_now(),
        "window_end": _iso_utc(end),
    }
