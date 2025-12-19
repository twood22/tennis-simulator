import pandas as pd
import os
from typing import Dict, Tuple, List, Set

class TennisDataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.player_data = {}
        self.fallback_warnings = {}
        self.load_all_data()
    
    def clean_percentage(self, value):
        """Convert percentage string to float"""
        if pd.isna(value) or value == '-' or value == '':
            return 0.0
        if isinstance(value, str) and value.endswith('%'):
            try:
                return float(value[:-1]) / 100.0
            except ValueError:
                return 0.0
        try:
            float_val = float(value)
            return float_val / 100.0 if float_val > 1 else float_val
        except (ValueError, TypeError):
            return 0.0
    
    def clean_numeric(self, value):
        """Convert numeric string to float"""
        if pd.isna(value) or value == '-' or value == '':
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def load_csv_data(self, filename: str) -> pd.DataFrame:
        """Load and clean CSV data"""
        filepath = os.path.join(self.data_dir, filename)
        df = pd.read_csv(filepath)
        
        # Clean percentage columns
        percentage_cols = [col for col in df.columns if 'pct' in col.lower() or 'win_pct' in col.lower()]
        # Also handle double_fault_per_second_serve which is a percentage but doesn't have 'pct' in the name
        if 'double_fault_per_second_serve' in df.columns:
            percentage_cols.append('double_fault_per_second_serve')
        for col in percentage_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.clean_percentage)
        
        # Clean numeric columns that might have '-' values
        numeric_cols = [
            'dominance_ratio', 'ranking',
            'first_serve_in_pct', 'first_serve_win_pct', 'second_serve_win_pct',
            'vs_first_serve_win_pct', 'vs_second_serve_win_pct',
            'break_point_conversion_pct', 'break_point_save_pct'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.clean_numeric)
        
        return df
    
    def load_all_data(self):
        """Load all CSV files and create unified data structure"""
        # Load all CSV files
        serve_df = self.load_csv_data("Tennis abstract - serve.csv")
        return_df = self.load_csv_data("Tennis abstract - return.csv")
        breaks_df = self.load_csv_data("Tennis abstract - breaks.csv")
        more_df = self.load_csv_data("Tennis abstract - more.csv")
        
        # Get all unique players and surfaces
        all_players = set()
        all_surfaces = set()
        
        for df in [serve_df, return_df, breaks_df, more_df]:
            all_players.update(df['player_name'].unique())
            all_surfaces.update(df['surface'].unique())
        
        # Build unified data structure
        for player in all_players:
            self.player_data[player] = {}
            self.fallback_warnings[player] = {}
            
            for surface in all_surfaces:
                # Try to get data for this surface
                player_surface_data = self._get_player_surface_data(
                    player, surface, serve_df, return_df, breaks_df, more_df
                )
                
                if player_surface_data:
                    self.player_data[player][surface] = player_surface_data
                    self.fallback_warnings[player][surface] = False
                else:
                    # Use hard court data as fallback
                    fallback_data = self._get_player_surface_data(
                        player, 'hard', serve_df, return_df, breaks_df, more_df
                    )
                    if fallback_data:
                        self.player_data[player][surface] = fallback_data
                        self.fallback_warnings[player][surface] = True
                    else:
                        # No data available for this player
                        continue
    
    def _get_player_surface_data(self, player: str, surface: str, serve_df, return_df, breaks_df, more_df) -> Dict:
        """Get all statistics for a player on a specific surface"""
        serve_data = serve_df[(serve_df['player_name'] == player) & (serve_df['surface'] == surface)]
        return_data = return_df[(return_df['player_name'] == player) & (return_df['surface'] == surface)]
        breaks_data = breaks_df[(breaks_df['player_name'] == player) & (breaks_df['surface'] == surface)]
        more_data = more_df[(more_df['player_name'] == player) & (more_df['surface'] == surface)]
        
        if serve_data.empty or return_data.empty or breaks_data.empty or more_data.empty:
            return None
        
        serve_row = serve_data.iloc[0]
        return_row = return_data.iloc[0]
        breaks_row = breaks_data.iloc[0]
        more_row = more_data.iloc[0]
        
        # Combine all statistics
        stats = {
            # Serve statistics
            'ranking': serve_row['ranking'],
            'first_serve_in_pct': serve_row['first_serve_in_pct'],
            'first_serve_win_pct': serve_row['first_serve_win_pct'],
            'second_serve_win_pct': serve_row['second_serve_win_pct'],
            'double_fault_per_second_serve': serve_row['double_fault_per_second_serve'],
            'ace_pct': serve_row['ace_pct'],
            'double_fault_pct': serve_row['double_fault_pct'],
            
            # Return statistics
            'vs_first_serve_win_pct': return_row['vs_first_serve_win_pct'],
            'vs_second_serve_win_pct': return_row['vs_second_serve_win_pct'],
            'return_points_won': return_row['return_points_won'],
            
            # Break point statistics
            'break_point_conversion_pct': breaks_row['break_point_conversion_pct'],
            'break_point_save_pct': breaks_row['break_point_save_pct'],
            
            # Additional statistics
            'dominance_ratio': more_row['dominance_ratio'],
            'total_points_won_pct': more_row['total_points_won_pct'],
            'tiebreak_win_pct': more_row['tiebreak_win_pct'],
            'set_win_pct': more_row['set_win_pct'],
            'game_win_pct': more_row['game_win_pct']
        }
        
        return stats
    
    def get_player_stats(self, player_name: str, surface: str) -> Tuple[Dict, bool]:
        """Get player statistics for a surface, returns (stats, is_fallback)"""
        if player_name not in self.player_data:
            raise ValueError(f"Player {player_name} not found in data")
        
        if surface not in self.player_data[player_name]:
            raise ValueError(f"Surface {surface} not available for player {player_name}")
        
        stats = self.player_data[player_name][surface]
        is_fallback = self.fallback_warnings[player_name][surface]
        
        return stats, is_fallback
    
    def get_all_players(self) -> List[Dict]:
        """Get list of all players with their rankings and available surfaces"""
        players = []
        for player_name, surfaces_data in self.player_data.items():
            if not surfaces_data:
                continue
                
            # Get ranking from any available surface (they should be the same)
            ranking = None
            available_surfaces = []
            
            for surface, stats in surfaces_data.items():
                if stats:
                    available_surfaces.append(surface)
                    if ranking is None:
                        ranking = stats['ranking']
            
            if available_surfaces:
                players.append({
                    'name': player_name,
                    'ranking': ranking,
                    'surfaces': available_surfaces
                })
        
        # Sort by ranking
        players.sort(key=lambda x: x['ranking'])
        return players
    
    def get_fallback_warning(self, player_name: str, surface: str) -> str:
        """Get fallback warning message if applicable"""
        if (player_name in self.fallback_warnings and 
            surface in self.fallback_warnings[player_name] and 
            self.fallback_warnings[player_name][surface]):
            return f"{player_name} using hard court data for {surface} surface"
        return None