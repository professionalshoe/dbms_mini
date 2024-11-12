from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify
import requests, mysql.connector, json
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

import re

def extract_termination(pgn):
    match = re.search(r'\[Termination "(.*?)"\]', pgn)
    return match.group(1) if match else "Unknown"

# Add this function to your existing imports
app.jinja_env.filters['extract_termination'] = extract_termination

def create_db_connection():
    connection = mysql.connector.connect(host='localhost', user='root', password='priyanshu', database='chess_analyzer')
    return connection

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('home.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['player_id']
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
        
        cursor.close()
        connection.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = create_db_connection()
        cursor = connection.cursor()
        
        hashed_password = generate_password_hash(password)
        
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            connection.commit()
            player_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO win_log (player_id, white_win, black_win, no_of_draws) VALUES (%s, %s, %s, %s)", 
                           (player_id, 0, 0, 0))
            connection.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username already exists', 'error')
        finally:
            cursor.close()
            connection.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/view_games')
def view_games():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('view_games.html')

@app.route('/fetch', methods=['POST'])
def fetch():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    username = request.form['username']
    req_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    req_response = requests.get(req_url, headers=headers)
    if req_response.status_code == 200:
        game_archives = req_response.json()
        if game_archives:
            game_archive_latest_month = game_archives["archives"][-1]
            latest_month_game_data = requests.get(game_archive_latest_month, headers=headers)

            if latest_month_game_data.status_code == 200:
                return render_template('view_games.html', games=latest_month_game_data.json()["games"], username=username)
            else:
                return render_template('view_games.html', error=f"Couldn't fetch latest month game data. Status code:{latest_month_game_data.status_code}", username=username)
        else:
            return render_template('view_games.html', error=f"Archives are empty for the user {username}", username=username)
    else:
        return render_template('view_games.html', error=f"Couldn't fetch data for user {username}. Status code:{req_response.status_code}", username=username)

@app.route('/save_game', methods=['POST'])
def save_game():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    game_data = request.form.get('game_data')
    
    if not game_data:
        return render_template('view_games.html', error="No game data received.")
    
    try:
        game = json.loads(game_data)
    except json.JSONDecodeError as err:
        return render_template('view_games.html', error=f"Error parsing game data: {err}")
    
    game_pgn = game.get('pgn', '')
    game_white = game.get('white', {}).get('username', '')
    game_black = game.get('black', {}).get('username', '')
    game_id = game.get('url', '')
    game_white_result=game.get('white',{}).get('result',{})
    game_black_result=game.get('black',{}).get('result',{})
    connection = create_db_connection()
    cursor = connection.cursor()

    try:
        insert_game_data_query = """
            INSERT INTO game_data (game_id, white_player, black_player, white_result, black_result, moves)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values_game_data = (
            game_id, 
            game_white, 
            game_black, 
            game.get('white', {}).get('result', ''), 
            game.get('black', {}).get('result', ''), 
            game_pgn
        )
        cursor.execute(insert_game_data_query, values_game_data)

        insert_saved_game_query = """
            INSERT INTO saved_games (player_id, chess_com_game_id)
            VALUES (%s, %s)
        """
        values_saved_game = (session['user_id'], game_id)
        cursor.execute(insert_saved_game_query, values_saved_game)
        if(game_white_result=="win"):
            insert_winlog_query="""
                update win_log
                set white_win=white_win+1
                where player_id=(select player_id from users where username=%s)
            """
            cursor.execute(insert_winlog_query,(session['username'],))
        elif(game_black_result=="win"):
            insert_winlog_query="""
                update win_log
                set black_win=black_win+1
                where player_id=(select player_id from users where username=%s)
            """
            cursor.execute(insert_winlog_query,(session['username'],))
        elif(game_black_result=="agreed" or game_black_result=="repetition" or game_black_result=="timevsinsufficient" or game_black_result=="stalemate"):
            insert_winlog_query="""
                update win_log
                set no_of_draws=no_of_draws+1
                where player_id=(select player_id from users where username=%s)
            """
            cursor.execute(insert_winlog_query,(session['username'],))
        connection.commit()
        return render_template('view_games.html', success="Game saved successfully")
    except mysql.connector.IntegrityError:
        return render_template('view_games.html', error="Game already exists")
    except mysql.connector.Error as err:
        return render_template('view_games.html', error=f"Error saving game: {err}")
    finally:
        cursor.close()
        connection.close()

@app.route('/saved_games')
def saved_games():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
            SELECT gd.id, gd.white_player, gd.black_player, gd.white_result, gd.black_result
            FROM game_data gd
            JOIN saved_games sg ON gd.game_id = sg.chess_com_game_id
            WHERE sg.player_id = %s
        """
        cursor.execute(query, (session['user_id'],))
        saved_games = cursor.fetchall()
        return render_template('saved_games.html', saved_games=saved_games)
    except mysql.connector.Error as err:
        return render_template('saved_games.html', error=f"Error fetching saved games: {err}")
    finally:
        cursor.close()
        connection.close()

@app.route('/delete_game', methods=['GET', 'POST'])
def delete_game():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        game_id = request.form.get('game_id')
        
        connection = create_db_connection()
        cursor = connection.cursor()
        
        try:
            
            cursor.execute("DELETE FROM game_data WHERE id = %s", (game_id,))
            
            connection.commit()
            flash('Game deleted successfully', 'success')
        except mysql.connector.Error as err:
            flash(f'Error deleting game: {err}', 'error')
        finally:
            cursor.close()
            connection.close()
        
        return redirect(url_for('saved_games'))
    
    return render_template('delete_game.html')





@app.route('/view_stats')
def view_stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    connection = create_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Fetch all users and their current stats from win_log
        query = """
            SELECT u.username, u.player_id, w.white_win, w.black_win, w.no_of_draws 
            FROM users u 
            JOIN win_log w ON u.player_id = w.player_id
        """
        cursor.execute(query)
        user_stats = cursor.fetchall()
        return render_template('view_stats.html', user_stats=user_stats)
    except mysql.connector.Error as err:
        flash(f'Error fetching statistics: {err}', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    app.run(debug=True)