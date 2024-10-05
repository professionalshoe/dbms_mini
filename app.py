from flask import Flask,request,render_template
import requests,mysql.connector,json
app=Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch',methods=['POST'])
def fetch():
    username=request.form['username']
    req_url=f"https://api.chess.com/pub/player/{username}/games/archives"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    req_response=requests.get(req_url,headers=headers)
    if(req_response.status_code==200):
        game_archives=req_response.json()
        if(game_archives):
            game_archive_latest_month=game_archives["archives"][-1]
            latest_month_game_data=requests.get(game_archive_latest_month,headers=headers)

            if(latest_month_game_data.status_code==200):
                print(latest_month_game_data)
                return render_template('index.html',games=latest_month_game_data.json()["games"],username=username)
            else:
                return render_template('index.html',error=f"Couldnt fetch latest month game data. Status code:{latest_month_game_data.status_code}",username=username)
        else:
            return render_template('index.html',error=f"archives are empty for the user {username}",username=username)

    else:
        return render_template('index.html',error=f"couldnt fetch data for usr {username}. Status code:{req_response.status_code}",username=username)


def create_db_connection():
    connection=mysql.connector.connect(host='localhost',user='root',password='priyanshu',database='chess_db')
    return connection

app.route('/save_game')
def save_game():
    game_data=request.form.get['game_data']
    username=request.form.get['username']
    game=json.loads(game_data)
    game_pgn=game_data['pgn']
    game_white=game_data['white']['username']
    game_black=game_data['black']['username']
    

    connection=create_db_connection()
    cursor=connection.cursor()



    try:
        cursor.execute(insert_query,values)
        connection.commit()
        return render_template('index.html',success="Game saved succesfully",username=username)
    except mysql.connector.Error as err:
        return render_template('index.html',error=f"error saving game {err}",username=username)
    finally:
        cursor.close()
        connection.close()



if __name__ == '__main__':
    app.run(debug=True)