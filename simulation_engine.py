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

class TennisSimulator:
    def __init__(self):
        self.random = random.Random()
        
    def simulate_point(self, server_stats: Dict, returner_stats: Dict, is_break_point: bool = False) -> bool:
        """
        Simulate a single point. Returns True if server wins, False if returner wins.
        """
        if is_break_point:
            # Use dedicated break point statistics
            server_win_prob = server_stats['break_point_save_pct']
            return self.random.random() < server_win_prob
        
        # Check if first serve is in
        first_serve_in = self.random.random() < server_stats['first_serve_in_pct']
        
        if first_serve_in:
            # First serve point calculation using dominance ratio weighting
            server_strength = server_stats['first_serve_win_pct']
            returner_strength = 1 - returner_stats['vs_first_serve_win_pct']
            
            server_dominance = server_stats['dominance_ratio']
            returner_dominance = returner_stats['dominance_ratio']
            
            total_dominance = server_dominance + returner_dominance
            win_prob = ((server_strength * server_dominance + 
                        returner_strength * returner_dominance) / total_dominance)
        else:
            # Second serve calculation
            second_serve_in_prob = 1 - server_stats['double_fault_per_second_serve']
            second_serve_in = self.random.random() < second_serve_in_prob
            
            if not second_serve_in:
                # Double fault - returner wins
                return False
            
            # Second serve point calculation
            server_strength = server_stats['second_serve_win_pct']
            returner_strength = 1 - returner_stats['vs_second_serve_win_pct']
            
            server_dominance = server_stats['dominance_ratio']
            returner_dominance = returner_stats['dominance_ratio']
            
            total_dominance = server_dominance + returner_dominance
            win_prob = ((server_strength * server_dominance + 
                        returner_strength * returner_dominance) / total_dominance)
        
        return self.random.random() < win_prob
    
    def simulate_game(self, server_stats: Dict, returner_stats: Dict, 
                     server_player: int, games_p1: int, games_p2: int) -> int:
        """
        Simulate a single game. Returns the winner (1 or 2).
        """
        score = GameScore()
        
        while True:
            # Check if this is a break point
            is_break_point = False
            if server_player == 1:
                # Player 1 serving, break point if Player 2 can win the game
                is_break_point = (score.player1_score >= 3 and 
                                score.player2_score >= score.player1_score)
            else:
                # Player 2 serving, break point if Player 1 can win the game
                is_break_point = (score.player2_score >= 3 and 
                                score.player1_score >= score.player2_score)
            
            # Simulate the point
            server_wins = self.simulate_point(server_stats, returner_stats, is_break_point)
            
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
    
    def simulate_tiebreak(self, p1_stats: Dict, p2_stats: Dict, starting_server: int) -> int:
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
            server_wins = self.simulate_point(server_stats, returner_stats)
            
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
    
    def simulate_set(self, p1_stats: Dict, p2_stats: Dict, starting_server: int) -> Tuple[int, int, int]:
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
                                           set_score.player2_games)
            
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
                    tiebreak_winner = self.simulate_tiebreak(p1_stats, p2_stats, current_server)
                    if tiebreak_winner == 1:
                        return 1, 7, 6
                    else:
                        return 2, 6, 7
            
            # Alternate server for next game
            current_server = 3 - current_server
    
    def simulate_match(self, p1_stats: Dict, p2_stats: Dict, format_type: str = "best3") -> MatchResult:
        """
        Simulate a complete match. Returns MatchResult.
        """
        sets_to_win = 3 if format_type == "best5" else 2
        p1_sets = 0
        p2_sets = 0
        set_scores = []
        current_server = 1  # Player 1 starts serving
        total_games = 0
        
        while p1_sets < sets_to_win and p2_sets < sets_to_win:
            set_winner, p1_games, p2_games = self.simulate_set(p1_stats, p2_stats, current_server)
            
            set_scores.append((p1_games, p2_games))
            total_games += p1_games + p2_games
            
            if set_winner == 1:
                p1_sets += 1
            else:
                p2_sets += 1
            
            # Alternate starting server for next set
            current_server = 3 - current_server
        
        winner = 1 if p1_sets > p2_sets else 2
        return MatchResult(winner=winner, set_scores=set_scores, total_games=total_games)
    
    def run_monte_carlo_simulation(self, p1_stats: Dict, p2_stats: Dict, 
                                 format_type: str = "best3", 
                                 num_simulations: int = 1000,
                                 progress_callback=None) -> Dict:
        """
        Run Monte Carlo simulation with specified number of matches.
        """
        p1_wins = 0
        p2_wins = 0
        set_distributions = {}
        
        for i in range(num_simulations):
            result = self.simulate_match(p1_stats, p2_stats, format_type)
            
            if result.winner == 1:
                p1_wins += 1
            else:
                p2_wins += 1
            
            # Track set score distribution
            p1_sets_won = sum(1 for p1_g, p2_g in result.set_scores if p1_g > p2_g)
            p2_sets_won = len(result.set_scores) - p1_sets_won
            set_key = f"{p1_sets_won}-{p2_sets_won}"
            set_distributions[set_key] = set_distributions.get(set_key, 0) + 1
            
            # Progress callback every 100 simulations
            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, num_simulations)
        
        return {
            "player1_wins": p1_wins,
            "player2_wins": p2_wins,
            "player1_win_pct": p1_wins / num_simulations,
            "player2_win_pct": p2_wins / num_simulations,
            "set_distributions": set_distributions,
            "total_simulations": num_simulations
        }