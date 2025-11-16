
import logging
import os
import uuid
from xml.parsers.expat import model
import psycopg2
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Db:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        self.conn_params = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        self.conn = None
        self.ensure_connection()
    
    def ensure_connection(self):
        try:
            # Check if the connection is open
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(**self.conn_params)
            else:
                # Test the connection
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
        except Exception as e:
            # Reconnect if the connection is invalid
            self.conn = psycopg2.connect(**self.conn_params)
    
    def insert_matches(self, matches):                
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            query = """
                INSERT INTO matches(match_id, kickoff, home_team, away_team, league, prediction, odd, overall_prob, parent_match_id, sub_type_id, bet_pick, special_bet_value, outcome_id)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (match_id) DO UPDATE SET
                    prediction = %s,
                    odd = %s,
                    overall_prob = %s     
                """
                
            values = [
                (
                    str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{match['match_id']}{match['prediction']}")),
                    match['start_time'],
                    match['home_team'].replace("'","''"),
                    match['away_team'].replace("'","''"),
                    match['category'].replace("'","''"),
                    match['prediction'],
                    match['odd'],
                    match['overall_prob'],
                    match['parent_match_id'],
                    match['sub_type_id'],
                    match['bet_pick'],
                    match['special_bet_value'],
                    match['outcome_id'],
                    match['prediction'],
                    match['odd'],
                    match['overall_prob']
                ) for match in matches
            ]
            cursor.executemany(query, values)
            self.conn.commit()
    
    def fetch_matches(self, day, comparator, status, limit=16): 
        self.ensure_connection()           
        with self.conn.cursor() as cur:
            query = f"""
            WITH m AS(
                SELECT * FROM matches
                WHERE kickoff::date {comparator} (CURRENT_TIMESTAMP + INTERVAL '3 hours')::date {day} {status}
                AND overall_prob >= 80
                ORDER BY odd DESC, overall_prob DESC
                LIMIT {limit}
            )
            SELECT * 
            FROM m
            ORDER BY kickoff, overall_prob, odd, match_id
            """
            cur.execute(query)
            return cur.fetchall()
           
    def fetch_unplaced_matches(self, profile_id): 
        self.ensure_connection()  
        matches = []         
        with self.conn.cursor() as cur:
            query = """
            WITH m AS(
                SELECT kickoff, home_team, away_team, odd, parent_match_id, sub_type_id, bet_pick, special_bet_value, outcome_id 
                FROM matches
                WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
            ),
            placed AS(
              SELECT parent_match_id 
              FROM betslips 
              WHERE profile_id = %s
            )
            SELECT * 
            FROM m
            WHERE parent_match_id NOT IN(
              SELECT parent_match_id FROM placed
            )
            ORDER BY kickoff
            """
            cur.execute(query, (profile_id,)) 
            for datum in cur.fetchall():
                match = {
                    'start_time': datum[0],
                    'home_team': datum[1],
                    'away_team': datum[2],
                    'odd': datum[3],
                    'parent_match_id': datum[4],
                    'sub_type_id': datum[5],
                    'bet_pick': datum[6],
                    'special_bet_value': datum[7],
                    'outcome_id': datum[8]
                }
                matches.append(match)
        return matches
    
    def fetch_predicted_match_ids(self): 
        self.ensure_connection()  
        parent_match_ids = set()         
        with self.conn.cursor() as cur:
            query = """
            SELECT parent_match_id
            FROM source_model
            WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
            """
            cur.execute(query) 
            for datum in cur.fetchall():
                parent_match_ids.add(datum[0])
        return parent_match_ids
    
    def fetch_last_prediction(self): 
        self.ensure_connection()       
        with self.conn.cursor() as cur:
            query = """
            SELECT MAX(kickoff)
            FROM source_model
            WHERE kickoff > (CURRENT_TIMESTAMP + INTERVAL '3 hours')
            """
            cur.execute(query) 
            datum = cur.fetchone()
        return datum[0]
    
    def add_bet_slip(self, profile_id, slips, code):
        """
        Add multiple bet slips for a profile.
        Each slip should be a dict with a 'parent_match_id' key.
        """
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO betslips(code, profile_id, parent_match_id)
                    VALUES(%s, %s, %s)
                """
                values = [
                    (code, profile_id, slip['parent_match_id']) for slip in slips
                ]
                cur.executemany(query, values)
                self.conn.commit()
        except Exception as e:
            logger.error("Error adding bet slips: %s", e)
    
    def update_match_results(self, match_id, home_results, away_results, status):        
        self.ensure_connection()
        with self.conn.cursor() as cur:
            query = """
                UPDATE matches SET
                    home_results = %s,
                    away_results = %s,
                    status = %s
                WHERE match_id = %s
            """
            
            cur.execute(query, (home_results, away_results, status, match_id)) 
            self.conn.commit()    
     
    def get_active_profiles(self):
        self.ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                query = """
                    SELECT phone, password
                    FROM profiles
                    WHERE is_active IS TRUE
                """
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error("Error fetching active profiles: %s", e)
            return []        
        
    def update_source_model(self, parent_match_id, model, kickoff):         
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO source_model(parent_match_id, model, kickoff)
                    VALUES(%s, %s, %s)
                """
                
                cur.execute(query, (parent_match_id, model, kickoff)) 
                self.conn.commit()  
        except Exception as e:
            logger.error("Error updating source model: %s", e)
            return []        
        
    def insert_jackpot_match(self, match, model, event_id, event_name, provider):    
        '''Insert a predicted jackpot match into the database.'''     
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO jackpot_matches(provider, start_time, event_id, event_name, parent_match_id, home_team, away_team, sub_type_id, bet_pick, outcome_id, overall_prob, model)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (parent_match_id, model) 
                        DO UPDATE SET
                            bet_pick = EXCLUDED.bet_pick,
                            outcome_id = EXCLUDED.outcome_id,
                            overall_prob = EXCLUDED.overall_prob
                """
                
                cur.execute(query, (
                        provider, 
                        match['start_time'], 
                        event_id, 
                        event_name,
                        match['parent_match_id'], 
                        match['home_team'], 
                        match['away_team'], 
                        match['sub_type_id'], 
                        match['bet_pick'], 
                        match['outcome_id'], 
                        match['overall_prob'], 
                        model
                    )) 
                self.conn.commit()  
        except Exception as e:
            logger.error("Error inserting jackpot match: %s", e)
        
        
    def insert_event(self, event):    
        '''Insert an event into the database.'''     
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                query = """
                    INSERT INTO events(id, start_time, home_team, away_team, bet_pick, odd, odd_change, tournament, category, sport)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) 
                        DO UPDATE SET
                            bet_pick = EXCLUDED.bet_pick,
                            odd = EXCLUDED.odd,
                            odd_change = EXCLUDED.odd_change
                """
                
                cur.execute(query, (
                        event['id'], 
                        event['start_time'], 
                        event['home_team'], 
                        event['away_team'], 
                        event['bet_pick'], 
                        event['odd'], 
                        event['odd_change'],
                        event['tournament'],
                        event['category'],
                        event['sport']
                    )) 
                self.conn.commit()  
        except Exception as e:
            logger.error("Error inserting event: %s", e)
     
    def get_started_events(self):
        self.ensure_connection()
        try:
            events = []
            with self.conn.cursor() as cursor:
                query = """
                    SELECT id, bet_pick, start_time, CURRENT_TIMESTAMP
                    FROM events
                    WHERE start_time < CURRENT_TIMESTAMP + INTERVAL '3 hours'
                       AND (status IS NULL OR status IN ('notstarted','inprogress'))
                """
                
                cursor.execute(query)
                for datum in cursor.fetchall():
                    events.append({
                        'id': datum[0],
                        'bet_pick': datum[1]
                    })
            return events
        except Exception as e:
            logger.error("Error fetching started events: %s", e)
            return []     
        
        
    def update_event_results(self, id, home_results, away_results, status):    
        '''Insert an event into the database.'''     
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                query = """
                    UPDATE events SET
                        home_results = %s,
                        away_results = %s,
                        status = %s
                    WHERE id = %s
                """
                
                cur.execute(query, (
                        home_results, 
                        away_results, 
                        status,
                        id
                    )) 
                self.conn.commit()  
        except Exception as e:
            logger.error("Error inserting event: %s", e)   
       