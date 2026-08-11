#!/usr/bin/env python3
"""Build simulator inputs from TennisMyLife's MIT-licensed match CSVs."""

import argparse
import csv
import hashlib
import io
import json
import re
import statistics
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REGISTRY_URL = "https://stats.tennismylife.org/api/data-files"
SOURCE_PAGE = "https://stats.tennismylife.org/tennis-match-database"
OUTPUT_FILES = {
    "serve": "Tennis abstract - serve.csv",
    "return": "Tennis abstract - return.csv",
    "breaks": "Tennis abstract - breaks.csv",
    "more": "Tennis abstract - more.csv",
}
STAT_FIELDS = (
    "ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms",
    "bpSaved", "bpFaced",
)
SURFACES = ("hard", "clay", "grass")
USER_AGENT = "tennis-simulator-refresh/1.0 (+https://github.com/twood22/tennis-simulator)"


def fetch(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read()


def pct(numerator, denominator):
    return "" if not denominator else f"{100 * numerator / denominator:.2f}%"


def ratio(numerator, denominator):
    return "" if not denominator else f"{numerator / denominator:.3f}"


def number(value, digits=2):
    return "" if value is None else f"{value:.{digits}f}".rstrip("0").rstrip(".")


def parse_int(row, field):
    try:
        return int(float(row[field]))
    except (KeyError, TypeError, ValueError):
        return None


def parse_match_date(value):
    return datetime.strptime(value, "%Y%m%d").date()


def add_score(stats, score, is_winner):
    if not score:
        return
    for token in score.split():
        if token.upper() in {"RET", "W/O", "DEF", "ABN"} or token.startswith("["):
            continue
        match = re.fullmatch(r"(\d+)-(\d+)(?:\(\d+\))?", token)
        if not match:
            continue
        winner_games, loser_games = map(int, match.groups())
        own, other = (winner_games, loser_games) if is_winner else (loser_games, winner_games)
        stats["games_won"] += own
        stats["games_lost"] += other
        stats["sets_won"] += own > other
        stats["sets_lost"] += own < other
        if {own, other} == {6, 7}:
            stats["tiebreaks"] += 1
            stats["tiebreaks_won"] += own == 7


def empty_stats():
    values = defaultdict(float)
    values["opponent_ranks"] = []
    return values


def add_player(stats, row, prefix, opponent_prefix, won):
    values = {field: parse_int(row, f"{prefix}_{field}") for field in STAT_FIELDS}
    opponent = {
        field: parse_int(row, f"{opponent_prefix}_{field}") for field in STAT_FIELDS
    }
    if any(value is None for value in (*values.values(), *opponent.values())):
        return False
    for candidate in (values, opponent):
        second_attempts = candidate["svpt"] - candidate["1stIn"]
        if (
            min(candidate.values()) < 0
            or candidate["svpt"] <= 0
            or candidate["SvGms"] <= 0
            or candidate["1stIn"] > candidate["svpt"]
            or candidate["1stWon"] > candidate["1stIn"]
            or candidate["2ndWon"] > second_attempts
            or candidate["df"] > second_attempts
            or candidate["bpSaved"] > candidate["bpFaced"]
        ):
            return False

    for field, value in values.items():
        stats[field] += value
    for field, value in opponent.items():
        stats[f"opp_{field}"] += value
    stats["matches"] += 1
    stats["wins"] += won
    opponent_rank = parse_int(row, "loser_rank" if prefix == "w" else "winner_rank")
    if opponent_rank:
        stats["opponent_ranks"].append(opponent_rank)
    add_score(stats, row.get("score", ""), won)
    return True


def read_matches(blobs, cutoff):
    matches = []
    seen = set()
    for name, blob in blobs.items():
        reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")))
        required = {"tourney_id", "tourney_date", "match_num", "winner_name", "loser_name", "surface"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{name} missing required columns: {sorted(missing)}")
        for row in reader:
            try:
                match_date = parse_match_date(row["tourney_date"])
            except (TypeError, ValueError):
                continue
            if match_date < cutoff or row["surface"].strip().lower() not in SURFACES:
                continue
            key = (
                row["tourney_id"], row["match_num"], row["winner_name"],
                row["loser_name"], row.get("score", ""),
            )
            if key not in seen:
                seen.add(key)
                matches.append((match_date, row))
    return matches


def aggregate(matches, min_matches=5):
    grouped = defaultdict(empty_stats)
    profiles = {}
    for match_date, row in sorted(matches, key=lambda item: item[0]):
        surface = row["surface"].strip().lower()
        for prefix, opponent_prefix, won in (("w", "l", True), ("l", "w", False)):
            player = row[f"{prefix}inner_name" if prefix == "w" else "loser_name"].strip()
            if not player:
                continue
            before = grouped[(player, surface)]["matches"]
            if not add_player(grouped[(player, surface)], row, prefix, opponent_prefix, won):
                continue
            add_player(grouped[(player, "all")], row, prefix, opponent_prefix, won)
            if grouped[(player, surface)]["matches"] > before:
                rank = parse_int(row, "winner_rank" if prefix == "w" else "loser_rank")
                profiles[player] = {
                    "ranking": rank,
                    "ioc": row.get("winner_ioc" if prefix == "w" else "loser_ioc", "").strip(),
                    "date": match_date.isoformat(),
                }
    return {
        key: stats for key, stats in grouped.items()
        if stats["matches"] >= min_matches
    }, profiles


def common(stats, profile, surface):
    return [surface, profile.get("ranking") or "", profile["name"], int(stats["matches"])]


def build_rows(grouped, profiles):
    outputs = {key: [] for key in OUTPUT_FILES}
    for (player, surface), stats in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        profile = {**profiles.get(player, {}), "name": player}
        base = common(stats, profile, surface)
        service_won = stats["1stWon"] + stats["2ndWon"]
        service_lost = stats["svpt"] - service_won
        second_attempts = stats["svpt"] - stats["1stIn"]
        second_in_play = second_attempts - stats["df"]
        breaks_allowed = stats["bpFaced"] - stats["bpSaved"]
        return_won = stats["opp_svpt"] - stats["opp_1stWon"] - stats["opp_2ndWon"]
        opp_second_attempts = stats["opp_svpt"] - stats["opp_1stIn"]
        breaks_made = stats["opp_bpFaced"] - stats["opp_bpSaved"]
        sets = stats["sets_won"] + stats["sets_lost"]
        games = stats["games_won"] + stats["games_lost"]
        record = f"{int(stats['wins'])}-{int(stats['matches'] - stats['wins'])}"
        opponents = stats["opponent_ranks"]

        outputs["serve"].append(base + [
            record, pct(stats["wins"], stats["matches"]), pct(service_won, stats["svpt"]),
            pct(service_won - stats["ace"], stats["svpt"] - stats["ace"] - stats["df"]),
            int(stats["ace"]), pct(stats["ace"], stats["svpt"]), int(stats["df"]),
            pct(stats["df"], stats["svpt"]), pct(stats["df"], second_attempts),
            pct(stats["1stIn"], stats["svpt"]), pct(stats["1stWon"], stats["1stIn"]),
            pct(stats["2ndWon"], second_attempts), pct(stats["2ndWon"], second_in_play),
            pct(stats["SvGms"] - breaks_allowed, stats["SvGms"]),
            number(stats["svpt"] / stats["SvGms"] if stats["SvGms"] else None),
            number(service_lost / stats["SvGms"] if stats["SvGms"] else None),
        ])
        outputs["return"].append(base + [
            pct(return_won, stats["opp_svpt"]),
            pct(return_won - stats["opp_df"], stats["opp_svpt"] - stats["opp_ace"] - stats["opp_df"]),
            pct(stats["opp_ace"], stats["opp_svpt"]), pct(stats["opp_df"], stats["opp_svpt"]),
            pct(stats["opp_1stIn"] - stats["opp_1stWon"], stats["opp_1stIn"]),
            pct(opp_second_attempts - stats["opp_2ndWon"], opp_second_attempts),
            pct(breaks_made, stats["opp_bpFaced"]),
            number(stats["opp_svpt"] / stats["opp_SvGms"] if stats["opp_SvGms"] else None),
            number(return_won / stats["opp_SvGms"] if stats["opp_SvGms"] else None),
            number(statistics.median(opponents), 1) if opponents else "",
            number(statistics.mean(opponents), 1) if opponents else "",
        ])
        outputs["breaks"].append(base + [
            pct(breaks_made, stats["opp_bpFaced"]), int(breaks_made), int(stats["opp_bpFaced"]),
            number(stats["opp_bpFaced"] / stats["opp_SvGms"] if stats["opp_SvGms"] else None),
            number(stats["opp_bpFaced"] / sets if sets else None),
            number(stats["opp_bpFaced"] / stats["matches"]),
            number(breaks_made / sets if sets else None), number(breaks_made / stats["matches"]),
            pct(stats["bpSaved"], stats["bpFaced"]), int(stats["bpSaved"]), int(stats["bpFaced"]),
            number(stats["bpFaced"] / stats["SvGms"] if stats["SvGms"] else None),
            number(stats["bpFaced"] / sets if sets else None), number(stats["bpFaced"] / stats["matches"]),
            number(breaks_allowed / sets if sets else None), number(breaks_allowed / stats["matches"]),
        ])
        outputs["more"].append(base + [
            ratio(return_won, service_lost), int(stats["svpt"] + stats["opp_svpt"]),
            pct(service_won + return_won, stats["svpt"] + stats["opp_svpt"]),
            int(stats["tiebreaks"]),
            f"{int(stats['tiebreaks_won'])}-{int(stats['tiebreaks'] - stats['tiebreaks_won'])}",
            pct(stats["tiebreaks_won"], stats["tiebreaks"]),
            ratio(stats["tiebreaks"], sets), int(sets),
            f"{int(stats['sets_won'])}-{int(stats['sets_lost'])}", pct(stats["sets_won"], sets),
            int(games), f"{int(stats['games_won'])}-{int(stats['games_lost'])}",
            pct(stats["games_won"], games), "", "", "",
        ])
    return outputs


HEADERS = {
    "serve": "surface,ranking,player_name,matches_played,match_record,match_win_pct,service_points_won,service_points_won_in_play,total_aces,ace_pct,double_faults,double_fault_pct,double_fault_per_second_serve,first_serve_in_pct,first_serve_win_pct,second_serve_win_pct,second_serve_win_pct_in_play,service_hold_pct,points_per_service_game,points_lost_per_service_game".split(","),
    "return": "surface,ranking,player_name,matches_played,return_points_won,return_points_won_in_play,vs_ace_pct,vs_double_fault_pct,vs_first_serve_win_pct,vs_second_serve_win_pct,break_point_conversion_pct,points_per_return_game,points_won_per_return_game,median_opponent_rank,mean_opponent_rank".split(","),
    "breaks": "surface,ranking,player_name,matches_played,break_point_conversion_pct,break_points_converted,break_point_chances,break_points_per_game,break_points_per_set,break_points_per_match,breaks_per_set,breaks_per_match,break_point_save_pct,break_points_saved,break_points_faced,break_points_faced_per_game,break_points_faced_per_set,break_points_faced_per_match,times_broken_per_set,times_broken_per_match".split(","),
    "more": "surface,ranking,player_name,matches_played,dominance_ratio,points,total_points_won_pct,tiebreaks_played,tiebreak_record,tiebreak_win_pct,tiebreaks_per_set,sets_played,set_record,set_win_pct,games_played,game_record,game_win_pct,time_per_match,minutes_per_set,seconds_per_point".split(","),
}


def write_outputs(outputs, output_dir, metadata):
    output_dir.mkdir(parents=True, exist_ok=True)
    for kind, filename in OUTPUT_FILES.items():
        destination = output_dir / filename
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(HEADERS[kind])
            writer.writerows(outputs[kind])
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--min-matches", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data")
    args = parser.parse_args()
    if args.days < 30 or args.min_matches < 1:
        parser.error("--days must be >= 30 and --min-matches must be >= 1")

    registry = json.loads(fetch(REGISTRY_URL))
    by_name = {item["name"]: item for item in registry["files"]}
    wanted = [
        f"{args.as_of.year - 1}.csv", f"{args.as_of.year}.csv",
        f"{args.as_of.year - 1}_challenger.csv", f"{args.as_of.year}_challenger.csv",
        "ongoing_tourneys.csv", "challenger_ongoing_tourneys.csv",
    ]
    missing = [name for name in wanted if name not in by_name]
    if missing:
        raise RuntimeError(f"Source registry missing files: {missing}")

    blobs = {name: fetch(by_name[name]["url"]) for name in wanted}
    matches = read_matches(blobs, args.as_of - timedelta(days=args.days))
    grouped, profiles = aggregate(matches, args.min_matches)
    outputs = build_rows(grouped, profiles)
    if not outputs["serve"] or not all(len(rows) == len(outputs["serve"]) for rows in outputs.values()):
        raise RuntimeError("Generated datasets are empty or inconsistent")

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": args.as_of.isoformat(),
        "window_days": args.days,
        "minimum_complete_matches": args.min_matches,
        "source": SOURCE_PAGE,
        "source_license": "MIT",
        "source_files": [
            {
                "name": name,
                "url": by_name[name]["url"],
                "modified": by_name[name].get("mtime"),
                "sha256": hashlib.sha256(blobs[name]).hexdigest(),
            }
            for name in wanted
        ],
        "unique_matches": len(matches),
        "player_surface_rows": len(outputs["serve"]),
    }

    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary)
        write_outputs(outputs, staged, metadata)
        # Validate through the production loader before replacing reviewed files.
        from data_loader import TennisDataLoader
        loader = TennisDataLoader(str(staged))
        if len(loader.get_all_players()) < 50:
            raise RuntimeError("Refresh produced fewer than 50 usable players")
        write_outputs(outputs, args.output_dir, metadata)
    print(f"Wrote {len(outputs['serve'])} player/surface rows from {len(matches)} matches")


if __name__ == "__main__":
    main()
