
import os
import uuid
import psycopg2
from dotenv import load_dotenv

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
                INSERT INTO matches(match_id, kickoff, home_team, away_team, prediction, odd, overall_prob, parent_match_id, sub_type_id, bet_pick, special_bet_value, outcome_id)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                AND sub_type_id = 1
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
            print(f"Error adding bet slips: {e}")
    
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
                    SELECT phone, password, profile_id
                    FROM profiles
                    WHERE is_active IS TRUE
                """
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching active profiles: {e}")
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
            print(f"Error updating source model: {e}")
                  
if __name__ == "__main__":
    crud = Db()

