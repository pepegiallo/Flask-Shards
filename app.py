from flask import Flask, render_template, redirect, url_for, request, flash
from renderer import ShardRenderer

app = Flask(__name__, template_folder='templates/rendered')
renderer = ShardRenderer()
renderer.update()

# Startseite
@app.route('/')
def index():
    persons = [
        {'name': 'Max', 'age': 20, 'city': 'Berlin'},
        {'name': 'Monika', 'age': 21, 'city': 'Hamburg'},
        {'name': 'Moritz', 'age': 30, 'city': 'München'},
        {'name': 'Erik', 'age': 25, 'city': 'Köln'},
        {'name': 'Lisa', 'age': 25, 'city': 'Frankfurt'}
    ]
    return render_template('index.html', persons=persons)

if __name__ == '__main__':
    app.run(debug=True)