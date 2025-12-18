import random
import numpy as np
from typing import Dict, Tuple, List
from dataclasses import dataclass

@dataclass
class GameScore:
    player1_score: int = 0
    player2_score: int = 0
    
    def get_tennis_score(self) -> Tuple[str, str]:
        """Convert numeric scores to tennis scoring (0, 15, 30, 40, A, game)"""
        score_map = {0: "0", 1: "15", 2: "30", 3: "40"}
        
        if self.player1_score >= 3 and self.player2_score >= 3:
            # Deuce situation
            if self.player1_score == self.player2_score:
                return "40", "40"
            elif self.player1_score > self.player2_score:
                return "A", "40"
            else:
                return "40", "A"
        
        p1_display = score_map.get(self.player1_score, "40")
        p2_display = score_map.get(self.player2_score, "40")
        return p1_display, p2_display

@dataclass
class SetScore:
    player1_games: int = 0
    player2_games: int = 0
    
@dataclass
class MatchResult:
    winner: int  # 1 or 2
    set_scores: List[Tuple[int, int]]
    total_games: int
    match_stats: Dict = None  # Track observed statistics during match

@dataclass
class MatchStats:
    """Track observed statistics during a match"""
    player1_first_serves_attempted: int = 0
    player1_first_serves_in: int = 0
    player1_first_serve_points_won: int = 0
    player1_first_serve_points_played: int = 0
    player1_second_serve_points_won: int = 0
    player1_second_serve_points_played: int = 0
    player1_break_points_saved: int = 0
    player1_break_points_faced: int = 0
    player1_break_points_converted: int = 0
    player1_break_points_opportunities: int = 0
    player1_double_faults: int = 0
    player1_second_serves_attempted: int = 0
    player1_return_points_played: int = 0
    player1_vs_first_serve_points_won: int = 0
    player1_vs_first_serve_points_played: int = 0
    player1_vs_second_serve_points_won: int = 0
    player1_vs_second_serve_points_played: int = 0
    
    player2_first_serves_attempted: int = 0
    player2_first_serves_in: int = 0
    player2_first_serve_points_won: int = 0
    player2_first_serve_points_played: int = 0
    player2_second_serve_points_won: int = 0
    player2_second_serve_points_played: int = 0
    player2_break_points_saved: int = 0
    player2_break_points_faced: int = 0
    player2_break_points_converted: int = 0
    player2_break_points_opportunities: int = 0
    player2_double_faults: int = 0
    player2_second_serves_attempted: int = 0
    player2_return_points_played: int = 0
    player2_vs_first_serve_points_won: int = 0
    player2_vs_first_serve_points_played: int = 0
    player2_vs_second_serve_points_won: int = 0
    player2_vs_second_serve_points_played: int = 0
    
    def get_observed_stats(self, player: int) -> Dict:
        """Calculate observed percentages for a player"""
        prefix = f"player{player}_"
        
        first_serves_attempted = getattr(self, f"{prefix}first_serves_attempted")
        first_serves_in = getattr(self, f"{prefix}first_serves_in")
        first_serve_points_won = getattr(self, f"{prefix}first_serve_points_won")
        first_serve_points_played = getattr(self, f"{prefix}first_serve_points_played")
        second_serve_points_won = getattr(self, f"{prefix}second_serve_points_won")
        second_serve_points_played = getattr(self, f"{prefix}second_serve_points_played")
        break_points_saved = getattr(self, f"{prefix}break_points_saved")
        break_points_faced = getattr(self, f"{prefix}break_points_faced")
        break_points_converted = getattr(self, f"{prefix}break_points_converted")
        break_points_opportunities = getattr(self, f"{prefix}break_points_opportunities")
        double_faults = getattr(self, f"{prefix}double_faults")
        second_serves_attempted = getattr(self, f"{prefix}second_serves_attempted")
        vs_first_serve_points_won = getattr(self, f"{prefix}vs_first_serve_points_won")
        vs_first_serve_points_played = getattr(self, f"{prefix}vs_first_serve_points_played")
        vs_second_serve_points_won = getattr(self, f"{prefix}vs_second_serve_points_won")
        vs_second_serve_points_played = getattr(self, f"{prefix}vs_second_serve_points_played")
        
        # Calculate second serve in percentage
        second_serves_in = second_serves_attempted - double_faults
        
        return {
            'first_serve_in_pct': first_serves_in / first_serves_attempted if first_serves_attempted > 0 else 0,
            'first_serve_win_pct': first_serve_points_won / first_serve_points_played if first_serve_points_played > 0 else 0,
            'second_serve_in_pct': second_serves_in / second_serves_attempted if second_serves_attempted > 0 else 0,
            'second_serve_win_pct': second_serve_points_won / second_serve_points_played if second_serve_points_played > 0 else 0,
            'vs_first_serve_win_pct': vs_first_serve_points_won / vs_first_serve_points_played if vs_first_serve_points_played > 0 else 0,
            'vs_second_serve_win_pct': vs_second_serve_points_won / vs_second_serve_points_played if vs_second_serve_points_played > 0 else 0,
            'break_point_save_pct': break_points_saved / break_points_faced if break_points_faced > 0 else 0,
            'break_point_conversion_pct': break_points_converted / break_points_opportunities if break_points_opportunities > 0 else 0,
            'double_fault_per_second_serve': double_faults / second_serves_attempted if second_serves_attempted > 0 else 0,
        }

class TennisSimulator:
    def __init__(self):
        self.random = random.Random()
        
    def simulate_point(self, server_stats: Dict, returner_stats: Dict, is_break_point: bool = False, 
                      server_player: int = 1, match_stats: MatchStats = None) -> bool:
        """
        Simulate a single point. Returns True if server wins, False if returner wins.
        """
        returner_player = 3 - server_player  # 1 becomes 2, 2 becomes 1
        
        if is_break_point:
            # Track break point statistics
            if match_stats:
                if server_player == 1:
                    match_stats.player1_break_points_faced += 1
                    match_stats.player2_break_points_opportunities += 1
                else:
                    match_stats.player2_break_points_faced += 1
                    match_stats.player1_break_points_opportunities += 1
            
            # Use dedicated break point statistics
            server_win_prob = server_stats['break_point_save_pct']
            server_wins = self.random.random() < server_win_prob
            
            # Track break point saves and conversions
            if match_stats:
                if server_wins:
                    if server_player == 1:
                        match_stats.player1_break_points_saved += 1
                    else:
                        match_stats.player2_break_points_saved += 1
                else:
                    # Returner converted the break point
                    if returner_player == 1:
                        match_stats.player1_break_points_converted += 1
                    else:
                        match_stats.player2_break_points_converted += 1
                    
            return server_wins
        
        # Track first serve attempt
        if match_stats:
            if server_player == 1:
                match_stats.player1_first_serves_attempted += 1
            else:
                match_stats.player2_first_serves_attempted += 1
        
        # Check if first serve is in
        first_serve_in = self.random.random() < server_stats['first_serve_in_pct']
        
        if first_serve_in:
            # Track first serve in and returning stats
            if match_stats:
                if server_player == 1:
                    match_stats.player1_first_serves_in += 1
                    match_stats.player1_first_serve_points_played += 1
                    match_stats.player2_vs_first_serve_points_played += 1
                else:
                    match_stats.player2_first_serves_in += 1
                    match_stats.player2_first_serve_points_played += 1
                    match_stats.player1_vs_first_serve_points_played += 1
            
            # First serve point calculation using dominance ratio weighting
            server_strength = server_stats['first_serve_win_pct']
            returner_strength = 1 - returner_stats['vs_first_serve_win_pct']
            
            server_dominance = server_stats['dominance_ratio']
            returner_dominance = returner_stats['dominance_ratio']
            
            total_dominance = server_dominance + returner_dominance
            win_prob = ((server_strength * server_dominance + 
                        returner_strength * returner_dominance) / total_dominance)
                        
            server_wins = self.random.random() < win_prob
            
            # Track first serve point wins and returning stats
            if match_stats:
                if server_wins:
                    if server_player == 1:
                        match_stats.player1_first_serve_points_won += 1
                    else:
                        match_stats.player2_first_serve_points_won += 1
                else:
                    # Returner won the point
                    if returner_player == 1:
                        match_stats.player1_vs_first_serve_points_won += 1
                    else:
                        match_stats.player2_vs_first_serve_points_won += 1
                    
            return server_wins
        else:
            # Track second serve attempt
            if match_stats:
                if server_player == 1:
                    match_stats.player1_second_serves_attempted += 1
                else:
                    match_stats.player2_second_serves_attempted += 1
            
            # Second serve calculation
            second_serve_in_prob = 1 - server_stats['double_fault_per_second_serve']
            second_serve_in = self.random.random() < second_serve_in_prob
            
            if not second_serve_in:
                # Track double fault
                if match_stats:
                    if server_player == 1:
                        match_stats.player1_double_faults += 1
                    else:
                        match_stats.player2_double_faults += 1
                # Double fault - returner wins
                return False
            
            # Track second serve point and returning stats
            if match_stats:
                if server_player == 1:
                    match_stats.player1_second_serve_points_played += 1
                    match_stats.player2_vs_second_serve_points_played += 1
                else:
                    match_stats.player2_second_serve_points_played += 1
                    match_stats.player1_vs_second_serve_points_played += 1
            
            # Second serve point calculation
            server_strength = server_stats['second_serve_win_pct']
            returner_strength = 1 - returner_stats['vs_second_serve_win_pct']
            
            server_dominance = server_stats['dominance_ratio']
            returner_dominance = returner_stats['dominance_ratio']
            
            total_dominance = server_dominance + returner_dominance
            win_prob = ((server_strength * server_dominance + 
                        returner_strength * returner_dominance) / total_dominance)
                        
            server_wins = self.random.random() < win_prob
            
            # Track second serve point wins and returning stats
            if match_stats:
                if server_wins:
                    if server_player == 1:
                        match_stats.player1_second_serve_points_won += 1
                    else:
                        match_stats.player2_second_serve_points_won += 1
                else:
                    # Returner won the point
                    if returner_player == 1:
                        match_stats.player1_vs_second_serve_points_won += 1
                    else:
                        match_stats.player2_vs_second_serve_points_won += 1
                    
            return server_wins
    
    def simulate_game(self, server_stats: Dict, returner_stats: Dict, 
                     server_player: int, games_p1: int, games_p2: int, match_stats: MatchStats = None) -> int:
        """
        Simulate a single game. Returns the winner (1 or 2).
        """
        score = GameScore()
        
        while True:
            # Check if this is a break point (returner can win game on next point)
            # Break point occurs when returner has 40+ (score >= 3) AND is ahead
            is_break_point = False
            if server_player == 1:
                # Player 1 serving, break point if Player 2 can win the game
                # Returner (P2) needs score >= 3 (40 or Ad) AND must be ahead
                is_break_point = (score.player2_score >= 3 and
                                score.player2_score > score.player1_score)
            else:
                # Player 2 serving, break point if Player 1 can win the game
                # Returner (P1) needs score >= 3 (40 or Ad) AND must be ahead
                is_break_point = (score.player1_score >= 3 and
                                score.player1_score > score.player2_score)
            
            # Simulate the point
            server_wins = self.simulate_point(server_stats, returner_stats, is_break_point, server_player, match_stats)
            
            if server_wins:
                if server_player == 1:
                    score.player1_score += 1
                else:
                    score.player2_score += 1
            else:
                if server_player == 1:
                    score.player2_score += 1
                else:
                    score.player1_score += 1
            
            # Check for game end
            if score.player1_score >= 4 and score.player1_score - score.player2_score >= 2:
                return 1
            elif score.player2_score >= 4 and score.player2_score - score.player1_score >= 2:
                return 2
    
    def simulate_tiebreak(self, p1_stats: Dict, p2_stats: Dict, starting_server: int, match_stats: MatchStats = None) -> int:
        """
        Simulate a tiebreak. Returns the winner (1 or 2).
        """
        p1_points = 0
        p2_points = 0
        points_played = 0
        current_server = starting_server
        
        while True:
            # Determine server and returner stats
            if current_server == 1:
                server_stats = p1_stats
                returner_stats = p2_stats
            else:
                server_stats = p2_stats
                returner_stats = p1_stats
            
            # Simulate point
            server_wins = self.simulate_point(server_stats, returner_stats, False, current_server, match_stats)
            
            if (current_server == 1 and server_wins) or (current_server == 2 and not server_wins):
                p1_points += 1
            else:
                p2_points += 1
            
            points_played += 1
            
            # Check for tiebreak end (first to 7, win by 2)
            if p1_points >= 7 and p1_points - p2_points >= 2:
                return 1
            elif p2_points >= 7 and p2_points - p1_points >= 2:
                return 2
            
            # Server rotation: serve 1 point, then alternate every 2 points
            if points_played == 1 or (points_played > 1 and (points_played - 1) % 2 == 0):
                current_server = 3 - current_server  # Switch between 1 and 2
    
    def simulate_set(self, p1_stats: Dict, p2_stats: Dict, starting_server: int, match_stats: MatchStats = None) -> Tuple[int, int, int]:
        """
        Simulate a set. Returns (winner, p1_games, p2_games).
        """
        set_score = SetScore()
        current_server = starting_server
        
        while True:
            # Determine server and returner stats for this game
            if current_server == 1:
                server_stats = p1_stats
                returner_stats = p2_stats
            else:
                server_stats = p2_stats
                returner_stats = p1_stats
            
            # Simulate the game
            game_winner = self.simulate_game(server_stats, returner_stats, 
                                           current_server, set_score.player1_games, 
                                           set_score.player2_games, match_stats)
            
            if game_winner == 1:
                set_score.player1_games += 1
            else:
                set_score.player2_games += 1
            
            # Check for set end
            if set_score.player1_games >= 6 or set_score.player2_games >= 6:
                # Check for regular set win (6+ games, lead of 2+)
                if (set_score.player1_games >= 6 and 
                    set_score.player1_games - set_score.player2_games >= 2):
                    return 1, set_score.player1_games, set_score.player2_games
                elif (set_score.player2_games >= 6 and 
                      set_score.player2_games - set_score.player1_games >= 2):
                    return 2, set_score.player1_games, set_score.player2_games
                elif set_score.player1_games == 6 and set_score.player2_games == 6:
                    # Tiebreak needed
                    tiebreak_winner = self.simulate_tiebreak(p1_stats, p2_stats, current_server, match_stats)
                    if tiebreak_winner == 1:
                        return 1, 7, 6
                    else:
                        return 2, 6, 7
            
            # Alternate server for next game
            current_server = 3 - current_server
    
    def simulate_match(self, p1_stats: Dict, p2_stats: Dict, format_type: str = "best3", track_stats: bool = False) -> MatchResult:
        """
        Simulate a complete match. Returns MatchResult.
        """
        sets_to_win = 3 if format_type == "best5" else 2
        p1_sets = 0
        p2_sets = 0
        set_scores = []
        current_server = 1  # Player 1 starts serving
        total_games = 0
        
        # Initialize match stats tracking if requested
        match_stats = MatchStats() if track_stats else None
        
        while p1_sets < sets_to_win and p2_sets < sets_to_win:
            set_winner, p1_games, p2_games = self.simulate_set(p1_stats, p2_stats, current_server, match_stats)
            
            set_scores.append((p1_games, p2_games))
            total_games += p1_games + p2_games
            
            if set_winner == 1:
                p1_sets += 1
            else:
                p2_sets += 1
            
            # Alternate starting server for next set
            current_server = 3 - current_server
        
        winner = 1 if p1_sets > p2_sets else 2
        
        # Prepare match stats for return
        match_stats_dict = None
        if match_stats:
            match_stats_dict = {
                'player1': match_stats.get_observed_stats(1),
                'player2': match_stats.get_observed_stats(2)
            }
        
        return MatchResult(winner=winner, set_scores=set_scores, total_games=total_games, match_stats=match_stats_dict)
    
    def run_monte_carlo_simulation(self, p1_stats: Dict, p2_stats: Dict, 
                                 format_type: str = "best3", 
                                 num_simulations: int = 1000,
                                 progress_callback=None,
                                 track_detailed_stats: bool = False) -> Dict:
        """
        Run Monte Carlo simulation with specified number of matches.
        """
        p1_wins = 0
        p2_wins = 0
        set_distributions = {}
        
        # Aggregate observed statistics
        aggregated_stats = {
            'player1': {
                'first_serve_in_pct': 0,
                'first_serve_win_pct': 0,
                'second_serve_in_pct': 0,
                'second_serve_win_pct': 0,
                'vs_first_serve_win_pct': 0,
                'vs_second_serve_win_pct': 0,
                'break_point_save_pct': 0,
                'break_point_conversion_pct': 0,
                'double_fault_per_second_serve': 0,
                'count': 0
            },
            'player2': {
                'first_serve_in_pct': 0,
                'first_serve_win_pct': 0,
                'second_serve_in_pct': 0,
                'second_serve_win_pct': 0,
                'vs_first_serve_win_pct': 0,
                'vs_second_serve_win_pct': 0,
                'break_point_save_pct': 0,
                'break_point_conversion_pct': 0,
                'double_fault_per_second_serve': 0,
                'count': 0
            }
        }
        
        for i in range(num_simulations):
            # Track detailed stats for aggregation if requested
            track_stats = track_detailed_stats
            result = self.simulate_match(p1_stats, p2_stats, format_type, track_stats)
            
            if result.winner == 1:
                p1_wins += 1
            else:
                p2_wins += 1
            
            # Track set score distribution
            p1_sets_won = sum(1 for p1_g, p2_g in result.set_scores if p1_g > p2_g)
            p2_sets_won = len(result.set_scores) - p1_sets_won
            set_key = f"{p1_sets_won}-{p2_sets_won}"
            set_distributions[set_key] = set_distributions.get(set_key, 0) + 1
            
            # Aggregate observed statistics if available
            if result.match_stats:
                for player in ['player1', 'player2']:
                    stats = result.match_stats[player]
                    agg_stats = aggregated_stats[player]
                    for key in ['first_serve_in_pct', 'first_serve_win_pct', 'second_serve_in_pct', 'second_serve_win_pct', 
                               'vs_first_serve_win_pct', 'vs_second_serve_win_pct', 'break_point_save_pct', 
                               'break_point_conversion_pct', 'double_fault_per_second_serve']:
                        agg_stats[key] += stats[key]
                    agg_stats['count'] += 1
            
            # Progress callback
            if progress_callback and (i + 1) % max(1, num_simulations // 10) == 0:
                progress_callback(i + 1, num_simulations)
        
        # Calculate average observed statistics
        observed_stats = None
        if track_detailed_stats and aggregated_stats['player1']['count'] > 0:
            observed_stats = {}
            for player in ['player1', 'player2']:
                count = aggregated_stats[player]['count']
                if count > 0:
                    observed_stats[player] = {
                        key: aggregated_stats[player][key] / count
                        for key in ['first_serve_in_pct', 'first_serve_win_pct', 'second_serve_in_pct', 'second_serve_win_pct', 
                                   'vs_first_serve_win_pct', 'vs_second_serve_win_pct', 'break_point_save_pct', 
                                   'break_point_conversion_pct', 'double_fault_per_second_serve']
                    }
        
        result_dict = {
            "player1_wins": p1_wins,
            "player2_wins": p2_wins,
            "player1_win_pct": p1_wins / num_simulations,
            "player2_win_pct": p2_wins / num_simulations,
            "set_distributions": set_distributions,
            "total_simulations": num_simulations
        }
        
        if observed_stats:
            result_dict["observed_stats"] = observed_stats
            
        return result_dict