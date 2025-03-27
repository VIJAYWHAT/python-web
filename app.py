from flask import Flask, render_template


app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def home():
    
    name = "VJ"
    return render_template('home.html' , name = name)

if __name__ == '__main__':
    app.run(debug=True)