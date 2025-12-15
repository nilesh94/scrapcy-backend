from flask import Flask, jsonify

# Note: In a real app, you'd configure your database here
# and include auction/blog logic.

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to the Scrapcy Backend API!",
        "status": "Running",
        "service": "Auction/Blog Logic"
    })

if __name__ == '__main__':
    # This is usually overridden by the start command on Render
    app.run(debug=True)
