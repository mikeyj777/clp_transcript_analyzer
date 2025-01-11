from typing import Dict, List, Tuple, Optional
import logging
import voyageai
from utils.hand_query_parser import HandQueryParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryEmbeddingProcessor:
    def __init__(self, api_key: str):
        """Initialize the query embedding processor"""
        self.api_key = api_key
        self.client = voyageai.Client(api_key=self.api_key)
        self.parser = HandQueryParser()

    def _create_situation_chunk(self, parsed_query: Dict) -> str:
        """Create the situation chunk from parsed query"""
        components = []
        
        # Game information
        if parsed_query.get('game_info'):
            game_components = []
            if 'stakes' in parsed_query['game_info']:
                game_components.append(f"Stakes: {parsed_query['game_info']['stakes']}")
            if 'game_type' in parsed_query['game_info']:
                game_components.append(f"Game Type: {parsed_query['game_info']['game_type']}")
            if 'straddle' in parsed_query['game_info']:
                game_components.append("Straddle: Yes")
            if game_components:
                components.append(", ".join(game_components))
        
        # Position and stack size
        position_info = []
        if parsed_query.get('position'):
            position_info.append(f"Position: {parsed_query['position']}")
        if parsed_query.get('stack_size'):
            position_info.append(f"Stack Size: {parsed_query['stack_size']}")
        if position_info:
            components.append(", ".join(position_info))
            
        # Player information
        if parsed_query.get('player_info'):
            player_components = []
            if 'num_players' in parsed_query['player_info']:
                player_components.append(f"{parsed_query['player_info']['num_players']}-handed")
            if 'villain_type' in parsed_query['player_info']:
                player_components.append(f"Villain: {parsed_query['player_info']['villain_type']}")
            if player_components:
                components.append(", ".join(player_components))
        
        # Hero cards
        if parsed_query.get('hero_cards'):
            components.append(f"Hero Cards: {parsed_query['hero_cards']}")
            
        return " | ".join(components)

    def _create_action_sequence_chunk(self, parsed_query: Dict) -> str:
        """Create action sequence chunk"""
        if not parsed_query.get('action_history'):
            return ""
            
        # Build action sequence
        actions = []
        
        if 'preflop_action' in parsed_query['action_history']:
            actions.append(f"preflop: {parsed_query['action_history']['preflop_action']}")
        
        # Add placeholders for other streets to maintain structure
        for street in ['flop', 'turn', 'river']:
            actions.append(f"{street}: ")
            
        return " -> ".join(actions)

    def _create_decision_chunks(self, parsed_query: Dict) -> List[Tuple[str, str]]:
        """Create decision point chunks for each street"""
        streets = ['preflop', 'flop', 'turn', 'river']
        chunks = []
        
        for street in streets:
            # Get any relevant decision context from parsed query
            decision_context = []
            
            if street == 'preflop' and parsed_query.get('action_history', {}).get('preflop_action'):
                decision_context.append(parsed_query['action_history']['preflop_action'])
                
            if parsed_query.get('position'):
                decision_context.append(f"from {parsed_query['position']}")
                
            if parsed_query.get('stack_size'):
                decision_context.append(f"with {parsed_query['stack_size']} stack")
                
            if decision_context:
                chunks.append((
                    f'{street}_decision',
                    f"{street} decision point: {' '.join(decision_context)}"
                ))
            else:
                chunks.append((f'{street}_decision', ''))
                
        return chunks

    def create_query_chunks(self, query: str) -> List[Tuple[str, str]]:
        """
        Create chunks for the query that match the transcript embedding structure
        """
        try:
            # Parse the query
            parsed_query = self.parser.parse_query(query)
            
            chunks = []
            
            # Add situation chunk
            situation = self._create_situation_chunk(parsed_query)
            chunks.append(('situation', situation))
            
            # Add action sequence chunk
            action_sequence = self._create_action_sequence_chunk(parsed_query)
            chunks.append(('action_sequence', action_sequence))
            
            # Add decision point chunks
            chunks.extend(self._create_decision_chunks(parsed_query))
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating query chunks: {str(e)}")
            raise

    def get_query_embeddings(
            self,
            query: str,
            model: str = "voyage-3-large"
        ) -> Optional[Dict[str, List[float]]]:
        """
        Generate embeddings for the query matching transcript embedding structure
        """
        try:
            # Create chunks
            chunks = self.create_query_chunks(query)
            
            # Generate embeddings
            texts = [text for _, text in chunks]
            chunk_types = [chunk_type for chunk_type, _ in chunks]
            
            embeddings = {}
            result = self.client.embed(
                texts=texts,
                model=model,
                input_type="query"  # Always use query type for search queries
            )
            
            for chunk_type, embedding in zip(chunk_types, result.embeddings):
                embeddings[chunk_type] = embedding
                
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating query embeddings: {str(e)}")
            return None

    def embed_query(self, query: str) -> Optional[Dict[str, List[float]]]:
        """
        Main method to generate embeddings for a query
        """
        try:
            return self.get_query_embeddings(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            return None